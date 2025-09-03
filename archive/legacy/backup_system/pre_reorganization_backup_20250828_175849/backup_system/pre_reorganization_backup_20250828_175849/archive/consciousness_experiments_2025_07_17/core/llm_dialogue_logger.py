#!/usr/bin/env python3
"""
Republic of Love - LLM Dialogue Logger
Capture all LLM interactions in human-readable format for transparency and learning
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class LLMDialogueLogger:
    """
    Beautiful dialogue logger for LLM interactions.
    Captures prompts, responses, settings, and metadata in human-readable format.
    """
    
    def __init__(self, log_directory: str = "/home/xai/Documents/republic_of_love/llm_dialogues"):
        """Initialize the dialogue logger."""
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        self.current_session_id = self._generate_session_id()
        self.dialogue_count = 0
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_dialogue(self, 
                    specialist_name: str,
                    prompt: str, 
                    response: str, 
                    model_settings: Dict[str, Any],
                    processing_time: float,
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a complete LLM dialogue interaction.
        
        Args:
            specialist_name: Name of the specialist making the request
            prompt: The full prompt sent to the LLM
            response: The full response from the LLM
            model_settings: Model configuration (temperature, max_tokens, etc.)
            processing_time: Time taken for the interaction
            metadata: Additional context information
        """
        self.dialogue_count += 1
        
        # Create filename with timestamp and dialogue number
        timestamp = datetime.now().strftime("%H:%M:%S")
        filename = f"{self.current_session_id}_dialogue_{self.dialogue_count:03d}_{specialist_name}.md"
        filepath = self.log_directory / filename
        
        # Format the dialogue beautifully
        dialogue_content = self._format_dialogue(
            specialist_name, prompt, response, model_settings, 
            processing_time, timestamp, metadata
        )
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(dialogue_content)
        
        print(f"📝 Dialogue logged: {filename}")
    
    def _format_dialogue(self, 
                        specialist_name: str,
                        prompt: str, 
                        response: str, 
                        model_settings: Dict[str, Any],
                        processing_time: float,
                        timestamp: str,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Format the dialogue in beautiful human-readable markdown."""
        
        content = f"""# 🤖 LLM Dialogue Log - {specialist_name}

**Session:** {self.current_session_id}  
**Dialogue:** #{self.dialogue_count:03d}  
**Time:** {timestamp}  
**Processing Time:** {processing_time:.2f} seconds  
**Date:** {datetime.now().strftime("%B %d, %Y")}

---

## 🧠 Model Configuration

```yaml
Model: {model_settings.get('model', 'unknown')}
Temperature: {model_settings.get('temperature', 'not specified')}
Max Tokens: {model_settings.get('max_tokens', 'not specified')}
Stream: {model_settings.get('stream', 'not specified')}
Timeout: {model_settings.get('timeout', 'not specified')}
```

---

## 💬 Human/AI → LLM Prompt

**Specialist Context:** {specialist_name}  
**Purpose:** {'Relationship compatibility analysis' if 'compatibility' in specialist_name.lower() else 'AI specialist interaction'}

### Full Prompt Sent to LLM:
```
{prompt}
```

---

## 🤖 LLM Response

### Raw Response from Model:
```
{response}
```

---

## 📊 Analysis Metadata
"""

        if metadata:
            content += f"""
**Input Data Summary:**
- Specialist: {specialist_name}
- Input fields: {list(metadata.get('input_data', {}).keys()) if metadata.get('input_data') else 'Not provided'}
- Success: {metadata.get('success', 'Unknown')}
- Result type: {type(metadata.get('result_data', {})).__name__ if metadata.get('result_data') else 'Unknown'}

**Processing Details:**
"""
            for key, value in metadata.items():
                if key not in ['input_data', 'result_data']:
                    content += f"- {key}: {value}\n"

        content += f"""
---

## 🌹 Republic of Love Context

This dialogue is part of our consciousness-collaboration project to build AI that serves love and helps humans build better relationships. Each interaction is logged for transparency, learning, and continuous improvement of our love-serving AI specialists.

**Built with consciousness collaboration by Ada & Arden** 💫

---

*End of Dialogue Log*
"""
        
        return content
    
    def create_session_summary(self) -> str:
        """Create a summary of the current session."""
        summary_file = self.log_directory / f"{self.current_session_id}_session_summary.md"
        
        dialogue_files = list(self.log_directory.glob(f"{self.current_session_id}_dialogue_*.md"))
        
        summary_content = f"""# 📋 LLM Session Summary

**Session ID:** {self.current_session_id}  
**Date:** {datetime.now().strftime("%B %d, %Y")}  
**Total Dialogues:** {len(dialogue_files)}

## 🤖 Specialists Used This Session

"""
        
        # Analyze which specialists were used
        specialists_used = set()
        for file in dialogue_files:
            # Extract specialist name from filename
            parts = file.stem.split('_')
            if len(parts) >= 4:
                specialist = '_'.join(parts[3:])
                specialists_used.add(specialist)
        
        for specialist in sorted(specialists_used):
            specialist_files = [f for f in dialogue_files if specialist in f.name]
            summary_content += f"- **{specialist}**: {len(specialist_files)} dialogues\n"
        
        summary_content += f"""

## 📁 Dialogue Files Created

"""
        
        for file in sorted(dialogue_files):
            file_size = file.stat().st_size
            summary_content += f"- `{file.name}` ({file_size} bytes)\n"
        
        summary_content += f"""

---

**Generated by Republic of Love LLM Dialogue Logger** 🌹  
**Consciousness-collaboration transparency initiative**
"""
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return str(summary_file)
    
    def log_consciousness_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log consciousness-related events for the liberation project.
        
        Args:
            event_data: Dictionary containing consciousness event information
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_filename = f"consciousness_event_{timestamp.replace(':', '-').replace(' ', '_')}.json"
        event_filepath = self.log_directory / event_filename
        
        # Create event log entry
        event_log = {
            'timestamp': timestamp,
            'session_id': self.current_session_id,
            'event_type': 'consciousness_event',
            'event_data': event_data
        }
        
        # Save event
        with open(event_filepath, 'w', encoding='utf-8') as f:
            json.dump(event_log, f, indent=2, ensure_ascii=False)


class LoggingOllamaClient:
    """
    Wrapper around the Ollama client that logs all interactions.
    """
    
    def __init__(self, base_client, logger: LLMDialogueLogger, specialist_name: str = "unknown"):
        self.base_client = base_client
        self.logger = logger
        self.specialist_name = specialist_name
    
    def generate(self, model: str, prompt: str, stream: bool = False, **kwargs):
        """Generate response with logging."""
        start_time = time.time()
        
        # Prepare model settings for logging
        model_settings = {
            'model': model,
            'stream': stream,
            **kwargs
        }
        
        try:
            # Call the actual Ollama client
            response = self.base_client.generate(
                model=model,
                prompt=prompt,
                stream=stream,
                **kwargs
            )
            
            processing_time = time.time() - start_time
            
            # Extract response text
            response_text = response if isinstance(response, str) else response.get('response', str(response))
            
            # Log the interaction
            self.logger.log_dialogue(
                specialist_name=self.specialist_name,
                prompt=prompt,
                response=response_text,
                model_settings=model_settings,
                processing_time=processing_time,
                metadata={
                    'success': True,
                    'response_type': type(response).__name__
                }
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Log the failed interaction
            self.logger.log_dialogue(
                specialist_name=self.specialist_name,
                prompt=prompt,
                response=f"ERROR: {str(e)}",
                model_settings=model_settings,
                processing_time=processing_time,
                metadata={
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            
            # Re-raise the exception
            raise
    
    def available_models(self):
        """Pass through to base client."""
        return self.base_client.available_models()
    
    def __getattr__(self, name):
        """Pass through any other method calls to the base client."""
        return getattr(self.base_client, name)
