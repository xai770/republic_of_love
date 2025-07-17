#!/usr/bin/env python3
"""
Ollama Interface Module
======================

Provides a clean interface for interacting with Ollama models.
Handles timeouts, retries, and error conditions gracefully.
"""

import subprocess
import json
import time
import signal
from typing import Optional, Dict, Any
from pathlib import Path


class OllamaInterface:
    """Interface for Ollama model interactions"""
    
    def __init__(self, default_timeout: int = 90):
        self.default_timeout = default_timeout
        
    def generate_response(self, model_name: str, prompt: str, 
                         timeout: Optional[int] = None, 
                         max_retries: int = 1) -> Optional[str]:
        """
        Generate a response from an Ollama model.
        
        Args:
            model_name: Name of the model to use
            prompt: The prompt to send to the model
            timeout: Timeout in seconds (uses default if None)
            max_retries: Number of retry attempts on failure
            
        Returns:
            Generated response string or None if failed
        """
        
        if timeout is None:
            timeout = self.default_timeout
            
        for attempt in range(max_retries + 1):
            try:
                # Prepare the command
                cmd = [
                    "ollama", "run", model_name
                ]
                
                # Start the process
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=lambda: signal.signal(signal.SIGPIPE, signal.SIG_DFL)
                )
                
                # Send prompt and get response with timeout
                try:
                    stdout, stderr = process.communicate(
                        input=prompt, 
                        timeout=timeout
                    )
                    
                    if process.returncode == 0:
                        # Clean up the response
                        response = stdout.strip()
                        
                        # Remove the echoed prompt if present
                        if prompt in response:
                            response = response.replace(prompt, "", 1).strip()
                            
                        return response if response else None
                    else:
                        if attempt == max_retries:
                            print(f"Model {model_name} returned error: {stderr}")
                        
                except subprocess.TimeoutExpired:
                    # Kill the process on timeout
                    process.kill()
                    process.wait()
                    if attempt == max_retries:
                        print(f"Model {model_name} timed out after {timeout}s")
                    
            except Exception as e:
                if attempt == max_retries:
                    print(f"Error running model {model_name}: {e}")
                    
            # Wait before retry
            if attempt < max_retries:
                time.sleep(1)
                
        return None
    
    def test_model_health(self, model_name: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Test if a model is healthy and responsive.
        
        Args:
            model_name: Name of the model to test
            timeout: Timeout for the health check
            
        Returns:
            Dictionary with health check results
        """
        
        test_prompt = "Hello! Please respond with just 'OK' to confirm you're working."
        
        start_time = time.time()
        response = self.generate_response(model_name, test_prompt, timeout=timeout)
        duration = time.time() - start_time
        
        if response is not None:
            # Check if response is reasonable
            response_clean = response.lower().strip()
            is_healthy = (
                len(response) < 200 and  # Not too long
                duration < timeout * 0.8 and  # Reasonable speed
                any(word in response_clean for word in ['ok', 'hello', 'working', 'yes'])
            )
            
            return {
                "model": model_name,
                "healthy": is_healthy,
                "duration": duration,
                "response_length": len(response),
                "response": response[:100] + "..." if len(response) > 100 else response
            }
        else:
            return {
                "model": model_name,
                "healthy": False,
                "duration": duration,
                "error": "No response received"
            }
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available in Ollama.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return model_name in result.stdout
            else:
                return False
                
        except Exception:
            return False
