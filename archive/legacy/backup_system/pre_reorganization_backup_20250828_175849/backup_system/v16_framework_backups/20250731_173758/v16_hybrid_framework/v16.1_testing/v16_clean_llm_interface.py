#!/usr/bin/env python3
"""
V16 Clean LLM Interface - Adapted from V14
==========================================

Clean, robust LLM interface for V16 hybrid template testing.
Adapted from Tracy's proven V14 system for reliable output capture.
"""

import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('v16_clean_llm')

class V16LLMInterface:
    """
    Clean LLM interface adapted from V14 for V16 testing
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 180):
        self.base_url = base_url
        self.timeout = timeout
        
    def call_model(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """
        Make a clean API call to Ollama model
        
        Args:
            model_name: Name of the Ollama model
            prompt: Full prompt text
            
        Returns:
            Dictionary with response data or error information
        """
        try:
            logger.info(f"🔄 Calling model {model_name}...")
            
            # Prepare API request
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_ctx": 8192
                }
            }
            
            # Make request with timeout
            start_time = time.time()
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            elapsed_time = time.time() - start_time
            
            # Check response status
            if response.status_code != 200:
                error_msg = f"API error {response.status_code}: {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "elapsed_time": elapsed_time
                }
            
            # Parse response
            try:
                result = response.json()
                
                if "response" not in result:
                    error_msg = "No 'response' field in API result"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "elapsed_time": elapsed_time
                    }
                
                logger.info(f"✅ Model {model_name} completed in {elapsed_time:.1f}s")
                
                return {
                    "success": True,
                    "response": result["response"],
                    "elapsed_time": elapsed_time,
                    "model": model_name,
                    "done": result.get("done", True),
                    "context": result.get("context", [])
                }
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {e}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "elapsed_time": elapsed_time
                }
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "elapsed_time": self.timeout
            }
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "elapsed_time": 0
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "elapsed_time": 0
            }

def test_model_availability(models: list) -> Dict[str, bool]:
    """
    Test which models are available in Ollama
    
    Args:
        models: List of model names to test
        
    Returns:
        Dictionary mapping model names to availability status
    """
    logger.info("🔍 Testing model availability...")
    
    interface = V16LLMInterface()
    availability = {}
    
    for model in models:
        try:
            # Simple test prompt
            result = interface.call_model(model, "Hello")
            availability[model] = result["success"]
            
            if result["success"]:
                logger.info(f"✅ {model} - Available")
            else:
                logger.warning(f"❌ {model} - Not available: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.warning(f"❌ {model} - Error testing: {e}")
            availability[model] = False
    
    return availability

if __name__ == "__main__":
    # Test script
    models = [
        "deepseek-r1:8b",
        "mistral-nemo:12b", 
        "qwen2.5:7b",
        "llama3.2:latest",
        "dolphin3:8b",
        "phi4-mini-reasoning:latest"
    ]
    
    print("V16 Clean LLM Interface Test")
    print("=" * 40)
    
    availability = test_model_availability(models)
    
    print("\nModel Availability Summary:")
    for model, available in availability.items():
        status = "✅ Available" if available else "❌ Not Available"
        print(f"  {model}: {status}")
