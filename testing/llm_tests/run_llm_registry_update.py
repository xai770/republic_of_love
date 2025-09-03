#!/usr/bin/env python3
"""
Unified LLM Registry Update Script
=================================

This script performs complete LLM model testing and registry generation in one operation:

1. Tests all available Ollama models with standardized prompts
2. Captures comprehensive conversation logs and performance data
3. Auto-generates the model registry document from test results
4. Updates rfa_latest/rfa_llm_model_registry.md with latest findings

Usage:
    python run_llm_registry_update.py

Features:
- 5-minute timeout for all operations
- Health check validation for all models
- Comprehensive job extraction testing
- Auto-cleanup of old result files
- Direct registry document generation

This is the single script needed to maintain our LLM model registry.
"""

import sys
import json
import time
import logging
import subprocess
import requests
import re
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import signal

# Add V14 to path
sys.path.append('/home/xai/Documents/ty_learn/production/v14')

# Import V14 modules with proper typing
try:
    from production.v14.config import Config  # type: ignore
    from production.v14.models import JobSkills  # type: ignore
except ImportError:
    # Fallback for runtime when sys.path is modified
    from config import Config  # type: ignore
    from models import JobSkills  # type: ignore

@dataclass
class HealthCheckResult:
    """Health check result for a model"""
    model: str
    passed: bool
    response_time: float
    response_text: str
    error_message: Optional[str]
    tested_at: str
    input_prompt: str = "Hello, how are you?"
    model_size: str = ""
    timeout_used: int = 300  # 5 minutes

@dataclass
class ConversationLog:
    """Complete conversation log for a model test"""
    prompt: str
    response: str
    duration: float
    success: bool
    error_message: Optional[str] = None
    api_params: Optional[Dict[str, Any]] = None

@dataclass
class CompleteTestResult:
    """Complete test result including health check and extraction tests"""
    model: str
    health_check: HealthCheckResult
    job_title: str
    conversation_logs: List[ConversationLog]
    status: str  # 'SUCCESS', 'HEALTH_FAILED', 'TIMEOUT', 'ERROR'
    error_message: Optional[str] = None
    exclusion_reason: Optional[str] = None
    tested_at: Optional[str] = None

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def get_all_models():
    """Get all available models from ollama"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ Failed to get model list: {result.stderr}", flush=True)
            return []
        
        models = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split()
                model_name = parts[0]
                size = parts[2] if len(parts) > 2 else "Unknown"
                models.append((model_name, size))
        
        return models
    except Exception as e:
        print(f"❌ Error getting models: {e}", flush=True)
        return []

def get_size_in_gb(size_str: str) -> float:
    """Convert size string to GB for sorting"""
    if 'GB' in size_str:
        try:
            return float(size_str.replace('GB', '').strip())
        except:
            return 999.0
    elif 'MB' in size_str:
        try:
            return float(size_str.replace('MB', '').strip()) / 1000.0
        except:
            return 0.1
    else:
        try:
            num = float(size_str)
            if num > 100:
                return num / 1000.0  # Convert to GB
            else:
                return num  # Assume GB
        except:
            return 999.0

def should_skip_model_upfront(model_name: str, size: str) -> tuple[bool, str]:
    """Determine if we should skip a model before any testing"""
    
    # Skip embedding models - these don't do text generation
    if 'bge-' in model_name or 'embed' in model_name.lower():
        return True, "Embedding model - not for text generation"
    
    # Skip vision models - specialized for image+text
    if 'vl:' in model_name or 'vision' in model_name.lower():
        return True, "Vision model - specialized for image tasks"
    
    # Only skip truly massive models (>15GB) that are guaranteed to timeout
    size_gb = get_size_in_gb(size)
    if size_gb > 15:
        return True, f"Extremely large ({size}, ~{size_gb:.1f}GB) - guaranteed timeout"
    
    return False, ""

def call_ollama_api(prompt: str, model: str, base_url: str = "http://localhost:11434", timeout_seconds: int = 300) -> tuple[str, float]:
    """Direct Ollama API call with timeout - default 5 minutes"""
    start_time = time.time()
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=timeout_seconds
        )
        
        if response.status_code == 200:
            result = response.json()
            duration = time.time() - start_time
            return result.get('response', ''), duration
        else:
            duration = time.time() - start_time
            return '', duration
            
    except Exception as e:
        duration = time.time() - start_time
        raise Exception(f"API call failed: {str(e)}")

def health_check_model(model: str, base_url: str = "http://localhost:11434") -> HealthCheckResult:
    """Perform basic health check on a model"""
    print(f"   🏥 Health check: 'Hello, how are you?'", flush=True)
    
    # Set up timeout for health check - 5 minutes
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)
    
    try:
        start_time = time.time()
        response, duration = call_ollama_api("Hello, how are you?", model, base_url, timeout_seconds=300)
        signal.alarm(0)
        
        # Basic validation - response should be reasonable
        actual_response = response
        if '<think>' in response:
            think_end = response.find('</think>')
            if think_end != -1:
                actual_response = response[think_end + 8:].strip()
        
        # Validation criteria
        passed = (
            len(actual_response.strip()) > 3 and
            len(response.strip()) < 2000 and
            not any(error_word in response.lower() for error_word in ['timeout', 'connection refused', 'server error']) and
            (
                any(word in actual_response.lower() for word in ['hello', 'hi', 'good', 'fine', 'well', 'thanks', 'i am', 'assist', 'help', 'ready', 'here']) or
                any(phrase in actual_response.lower() for phrase in ['artificial intelligence', 'language model', 'ai', 'digital entity', 'computer program'])
            )
        )
        
        return HealthCheckResult(
            model=model,
            passed=passed,
            response_time=duration,
            response_text=response[:200] + "..." if len(response) > 200 else response,
            error_message=None,
            input_prompt="Hello, how are you?",
            tested_at=datetime.now().isoformat()
        )
        
    except TimeoutError:
        signal.alarm(0)
        return HealthCheckResult(
            model=model,
            passed=False,
            response_time=300.0,
            response_text="",
            error_message="Health check timeout (5min)",
            tested_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        signal.alarm(0)
        return HealthCheckResult(
            model=model,
            passed=False,
            response_time=0.0,
            response_text="",
            error_message=f"Health check error: {str(e)}",
            input_prompt="Hello, how are you?",
            tested_at=datetime.now().isoformat()
        )

def test_model_comprehensive(model: str, job_data: dict, config: Config, health_check: HealthCheckResult) -> CompleteTestResult:
    """Test a single model comprehensively with timeout"""
    
    if not health_check.passed:
        return CompleteTestResult(
            model=model,
            health_check=health_check,
            job_title=job_data.get('title', 'Unknown Job'),
            conversation_logs=[],
            status='HEALTH_FAILED',
            error_message=health_check.error_message,
            exclusion_reason="Failed health check",
            tested_at=datetime.now().isoformat()
        )
    
    # Set up timeout for job extraction tests - 5 minutes
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)
    
    try:
        job_title = job_data.get('title', 'Unknown Job')
        job_description = job_data.get('description', '')
        conversation_logs = []
        
        print(f"   📊 Testing skill extraction...", flush=True)
        
        # Test skill extraction
        skill_template = config.get_template('skill_extraction')
        skill_prompt = skill_template.format(
            job_title=job_title,
            job_description=job_description[:3000]
        )
        
        skill_start = time.time()
        skill_response, skill_duration = call_ollama_api(skill_prompt, model, config.llm_base_url, 300)
        
        # Log skill extraction conversation
        conversation_logs.append(ConversationLog(
            prompt="Analyze this job posting and extract skills into t...",
            response=skill_response[:500] + ("..." if len(skill_response) > 500 else ""),
            duration=skill_duration,
            success=skill_response is not None
        ))
        
        print(f"   📝 Testing description generation...", flush=True)
        
        # Test description generation
        desc_template = config.get_template('concise_description')
        desc_prompt = desc_template.format(
            job_title=job_title,
            job_description=job_description[:2000]
        )
        
        desc_start = time.time()
        desc_response, desc_duration = call_ollama_api(desc_prompt, model, config.llm_base_url, 300)
        
        # Log description generation conversation
        conversation_logs.append(ConversationLog(
            prompt="Create a concise, professional summary for this jo...",
            response=desc_response[:500] + ("..." if len(desc_response) > 500 else ""),
            duration=desc_duration,
            success=desc_response is not None
        ))
        
        signal.alarm(0)  # Cancel timeout
        
        return CompleteTestResult(
            model=model,
            health_check=health_check,
            job_title=job_title,
            conversation_logs=conversation_logs,
            status='SUCCESS',
            error_message=None,
            exclusion_reason=None,
            tested_at=datetime.now().isoformat()
        )
        
    except TimeoutError:
        signal.alarm(0)
        return CompleteTestResult(
            model=model,
            health_check=health_check,
            job_title=job_data.get('title', 'Unknown Job'),
            conversation_logs=[],
            status='TIMEOUT',
            error_message='Job extraction timeout after 5 minutes',
            exclusion_reason="Too slow for production use (>5min)",
            tested_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        signal.alarm(0)
        return CompleteTestResult(
            model=model,
            health_check=health_check,
            job_title=job_data.get('title', 'Unknown Job'),
            conversation_logs=[],
            status='ERROR',
            error_message=str(e),
            exclusion_reason=f"Technical error: {str(e)}",
            tested_at=datetime.now().isoformat()
        )

def format_conversation_logs(logs: List[Dict[str, Any]]) -> str:
    """Format conversation logs for display"""
    if not logs:
        return "No conversation logs available"
    
    formatted = []
    for i, log in enumerate(logs, 1):
        prompt = log.get('prompt', '')
        response = log.get('response', '')
        duration = log.get('duration', 0)
        
        formatted.append(f"**{i}. {prompt}**\\n")
        formatted.append(f"```\\n{response[:500]}{'...' if len(response) > 500 else ''}\\n```\\n")
        formatted.append(f"- Duration: {duration:.1f}s\\n")
        if log.get('error_message'):
            formatted.append(f"- Error: {log.get('error_message')}\\n")
        formatted.append("")
    
    return "".join(formatted)

def generate_registry_md(results: List[Dict[str, Any]], output_file: str):
    """Generate the model registry markdown file"""
    
    # Separate results by status
    passing_models = [r for r in results if r['health_check']['passed']]
    failing_models = [r for r in results if not r['health_check']['passed']]
    
    # Sort by performance (for passing models)
    passing_models.sort(key=lambda x: x['health_check']['response_time'])
    
    current_time = datetime.now().strftime("%Y-%m-%d")
    
    md_content = f"""# RfA: LLM Model Registry and Experience Database
**Parent**: rfa_ty_learn  
**Status**: Active Development  
**Created**: 2025-08-29  
**Last Updated**: {current_time}  
**Auto-Generated**: From comprehensive test results

## Executive Summary

Comprehensive registry of all LLM models available in our Ollama installation with documented experience, performance characteristics, and use case recommendations. This serves as our institutional knowledge base for model selection across different tasks and projects.

**LATEST UPDATE ({current_time})**: Auto-generated from comprehensive testing results. Testing used 5-minute timeouts for both health checks and full extraction tasks.

## Model Inventory Overview

**Total Models**: {len(results)} models  
**Passed Health Check**: {len(passing_models)} models ({len(passing_models)/len(results)*100:.1f}%)  
**Failed Health Check**: {len(failing_models)} models ({len(failing_models)/len(results)*100:.1f}%)  

---

## Test Configuration

### Standard Inputs Used for All Models

**Health Check Prompt**: 
```
{results[0]['health_check']['input_prompt']}
```

**Job Extraction Test**:
- **Job Title**: {results[0]['job_title']}
- **Skills Extraction**: V14 skill_extraction template (3000 char limit)
- **Description Generation**: V14 concise_description template (2000 char limit)

**Timeouts**: 5 minutes (300 seconds) for all operations

---

## 🏆 PASSING MODELS (Health Check ✅)

"""

    # Add passing models
    for i, model in enumerate(passing_models, 1):
        health = model['health_check']
        
        md_content += f"""
### {i}. {model['model']} 
- **Health Check**: ✅ Passed ({health['response_time']:.1f}s)
- **Response**: 
```
{health['response_text']}
```
- **Model Size**: {health.get('model_size', '')}
- **Status**: {model['status']}
- **Tested**: {health['tested_at']}

**Conversation Logs**:
{format_conversation_logs(model.get('conversation_logs', []))}

"""

    # Add failing models
    md_content += f"""
---

## ❌ FAILED MODELS (Health Check ❌)

"""

    for i, model in enumerate(failing_models, 1):
        health = model['health_check']
        
        md_content += f"""
### {i}. {model['model']}
- **Health Check**: ❌ Failed ({health['response_time']:.1f}s)
- **Error**: {health.get('error_message', 'None')}
- **Response**: 
```
{health.get('response_text', 'No response')}
```
- **Model Size**: {health.get('model_size', '')}
- **Status**: {model['status']}
- **Exclusion Reason**: {model.get('exclusion_reason', 'Failed health check')}
- **Tested**: {health['tested_at']}

"""

    # Add footer
    md_content += f"""
---

## 📊 TESTING SUMMARY

### Health Check Results
- **✅ Passed**: {len(passing_models)} models ({len(passing_models)/len(results)*100:.1f}%)
- **❌ Failed**: {len(failing_models)} models ({len(failing_models)/len(results)*100:.1f}%)
- **📊 Total Coverage**: {len(results)}/28 models expected

### Configuration
- **Health Check Timeout**: 5 minutes (300 seconds)
- **Full Test Timeout**: 5 minutes (300 seconds)  
- **Input Standardization**: All models tested with identical prompts
- **Output Capture**: Complete conversation logs for analysis

---

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Source**: Comprehensive test results with 5-minute timeouts  
**Test Framework**: `testing/llm_tests/run_llm_registry_update.py`
"""

    # Write to file
    with open(output_file, 'w') as f:
        f.write(md_content)

def cleanup_old_results():
    """Clean up old test result files"""
    pattern = "comprehensive_test_results_*.json"
    current_dir = Path.cwd()
    
    # Keep only the 3 most recent files
    result_files = sorted(current_dir.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
    
    for old_file in result_files[3:]:  # Keep 3 most recent
        print(f"🧹 Cleaning up old result: {old_file.name}")
        old_file.unlink()

def run_comprehensive_testing():
    """Run comprehensive testing and generate registry"""
    
    print("🎯 UNIFIED LLM REGISTRY UPDATE", flush=True)
    print("=" * 70, flush=True)
    
    # Clean up old results first
    cleanup_old_results()
    
    # Get all models
    all_models = get_all_models()
    if not all_models:
        print("❌ No models found!", flush=True)
        return
    
    print(f"Found {len(all_models)} models total", flush=True)
    
    # Filter models and sort by size (smallest first)
    models_to_test = []
    skipped_models = []
    
    for model_name, size in all_models:
        should_skip, reason = should_skip_model_upfront(model_name, size)
        if should_skip:
            skipped_models.append((model_name, reason))
        else:
            models_to_test.append((model_name, size, get_size_in_gb(size)))
    
    # Sort by size (smallest first for faster early results)
    models_to_test.sort(key=lambda x: x[2])
    
    print(f"Testing: {len(models_to_test)} models (smallest first)", flush=True)
    print(f"Skipped upfront: {len(skipped_models)} models", flush=True)
    print()
    
    # Load test job
    job_file = Path('/home/xai/Documents/ty_learn/production/v14/data/postings/job63144.json')
    with open(job_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)['job_content']
    
    print(f"Test job: {job_data.get('title', 'Unknown')}...", flush=True)
    print()
    
    # Initialize config
    config_dir = Path('/home/xai/Documents/ty_learn/production/v14/config')
    config = Config.load_from_external(config_dir)
    
    # Test all models
    results = []
    
    for i, (model, size, size_gb) in enumerate(models_to_test, 1):
        print(f"🤖 [{i}/{len(models_to_test)}] Testing {model} ({size})", flush=True)
        
        # Health check first
        health_check = health_check_model(model, config.llm_base_url)
        
        if health_check.passed:
            print(f"   ✅ Health check passed ({health_check.response_time:.1f}s)", flush=True)
            result = test_model_comprehensive(model, job_data, config, health_check)
            
            if result.status == 'SUCCESS':
                total_duration = sum(log.duration for log in result.conversation_logs)
                print(f"   ✅ Success: {total_duration:.1f}s total, {len(result.conversation_logs)} interactions", flush=True)
            elif result.status == 'TIMEOUT':
                print(f"   ⏰ TIMEOUT after 5 minutes - EXCLUDED", flush=True)
            elif result.status == 'ERROR':
                print(f"   ❌ ERROR - EXCLUDED: {result.error_message}", flush=True)
        else:
            print(f"   ❌ Health check failed - EXCLUDED: {health_check.error_message or 'Invalid response'}", flush=True)
            result = CompleteTestResult(
                model=model,
                health_check=health_check,
                job_title=job_data.get('title', 'Unknown Job'),
                conversation_logs=[],
                status='HEALTH_FAILED',
                exclusion_reason=health_check.error_message or 'Invalid response',
                tested_at=datetime.now().isoformat()
            )
        
        results.append(result)
        print()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"comprehensive_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    
    print(f"💾 Test results saved: {results_file}", flush=True)
    
    # Generate registry
    print("🔄 Generating model registry...", flush=True)
    output_file = "../../rfa_latest/rfa_llm_model_registry.md"
    
    try:
        generate_registry_md([asdict(r) for r in results], output_file)
        print(f"✅ Registry generated: {output_file}", flush=True)
    except Exception as e:
        print(f"❌ Registry generation failed: {e}", flush=True)
        return
    
    # Print summary
    success_results = [r for r in results if r.status == 'SUCCESS']
    print()
    print("📊 FINAL SUMMARY", flush=True)
    print("-" * 50, flush=True)
    print(f"✅ Successful: {len(success_results)}", flush=True)
    print(f"❌ Failed: {len(results) - len(success_results)}", flush=True)
    print(f"📄 Registry updated: rfa_latest/rfa_llm_model_registry.md", flush=True)
    print()
    print("🎉 LLM Registry update complete!", flush=True)
    
    return results

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run comprehensive testing and registry generation
    try:
        results = run_comprehensive_testing()
    except KeyboardInterrupt:
        print("\n⚠️ Registry update interrupted by user", flush=True)
    except Exception as e:
        print(f"\n❌ Registry update failed: {e}", flush=True)
        raise
