#!/usr/bin/env python3
"""
Ollama integration for systerd-lite.
Provides AI-powered system management using Ollama models.

Configuration is loaded from .state/config.json:
{
    "ollama_url": "http://localhost:11434",
    "ollama_model": "gemma3:12b"
}
"""

import asyncio
import json
import logging
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "gemma3:12b"


def get_ollama_config() -> Dict[str, str]:
    """Load Ollama configuration from .state/config.json"""
    # Try multiple possible config locations
    config_paths = [
        Path(__file__).parent.parent / ".state" / "config.json",  # huggingface_space/.state/
        Path.cwd() / ".state" / "config.json",  # current dir/.state/
        Path(os.environ.get("SYSTERD_STATE_DIR", "")) / "config.json" if os.environ.get("SYSTERD_STATE_DIR") else None,
    ]
    
    for config_path in config_paths:
        if config_path and config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                return {
                    "url": config.get("ollama_url", DEFAULT_OLLAMA_URL),
                    "model": config.get("ollama_model", DEFAULT_OLLAMA_MODEL)
                }
            except Exception as e:
                logger.debug(f"Could not load config from {config_path}: {e}")
    
    return {
        "url": DEFAULT_OLLAMA_URL,
        "model": DEFAULT_OLLAMA_MODEL
    }


class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, base_url: str = None, model: str = None):
        # Load from config if not explicitly provided
        config = get_ollama_config()
        self.base_url = base_url if base_url is not None else config["url"]
        self.model = model if model is not None else config["model"]
        self.available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is available"""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.base_url}/api/tags"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                self.available = True
                logger.info(f"Ollama is available at {self.base_url}")
            else:
                logger.debug(f"Ollama not available at {self.base_url} (this is optional)")
        except Exception as e:
            logger.debug(f"Ollama check failed: {e} (optional feature)")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "available": self.available
        }
    
    async def generate(self, prompt: str, system: str = None, 
                      temperature: float = 0.7, max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate completion using Ollama"""
        if not self.available:
            return {
                "status": "error",
                "error": f"Ollama is not available at {self.base_url}",
                "hint": "Please ensure Ollama is running and accessible. You can configure the URL in Settings.",
                "current_config": {
                    "url": self.base_url,
                    "model": self.model
                }
            }
        
        try:
            import requests
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system:
                payload["system"] = system
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "status": "ok",
                "response": result.get("response", ""),
                "model": self.model,
                "done": result.get("done", False)
            }
        
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def chat(self, messages: List[Dict[str, str]], 
                   temperature: float = 0.7) -> Dict[str, Any]:
        """Chat completion using Ollama"""
        if not self.available:
            return {
                "status": "error",
                "error": f"Ollama is not available at {self.base_url}",
                "hint": "Please ensure Ollama is running and accessible. You can configure the URL in Settings.",
                "current_config": {
                    "url": self.base_url,
                    "model": self.model
                }
            }
        
        try:
            import requests
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            message = result.get("message", {})
            
            return {
                "status": "ok",
                "role": message.get("role", "assistant"),
                "content": message.get("content", ""),
                "model": self.model
            }
        
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_system_issue(self, issue_description: str, 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system issue and provide recommendations"""
        system_prompt = """You are systerd, an AI system administrator.
Analyze system issues and provide actionable recommendations.
Format your response as JSON with fields: analysis, recommendations, commands."""
        
        prompt = f"""Issue: {issue_description}

Context:
{json.dumps(context, indent=2)}

Analyze the issue and provide:
1. Root cause analysis
2. Recommended actions
3. Commands to execute (if any)"""
        
        result = await self.generate(prompt, system=system_prompt, temperature=0.3)
        
        if result["status"] == "ok":
            try:
                # Try to parse JSON response
                response_text = result["response"]
                # Extract JSON from response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                analysis = json.loads(response_text)
                return {
                    "status": "ok",
                    "analysis": analysis
                }
            except json.JSONDecodeError:
                # Return as plain text if not JSON
                return {
                    "status": "ok",
                    "analysis": {
                        "raw_response": result["response"]
                    }
                }
        
        return result
    
    async def suggest_optimization(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest system optimizations based on metrics"""
        prompt = f"""Based on the following system metrics, suggest optimizations:

{json.dumps(metrics, indent=2)}

Provide specific optimization recommendations for:
- CPU usage
- Memory management
- Disk I/O
- Network performance"""
        
        return await self.generate(prompt, temperature=0.5)


class OllamaManager:
    """Manage multiple Ollama models (optional)"""
    
    def __init__(self, base_url: str = None, model: str = None):
        # Load from config if not explicitly provided
        config = get_ollama_config()
        self.base_url = base_url if base_url is not None else config["url"]
        self.default_model = model if model is not None else config["model"]
        self.clients = {}
        self.fallback_model = self.default_model
        self.available = False
        
        # Initialize default model - check availability first
        client = OllamaClient(self.base_url, self.default_model)
        if client.available:
            self.clients[self.default_model] = client
            self.available = True
        else:
            # Store unavailable client for reference
            self.clients[self.default_model] = client
    
    def get_client(self, model: str = None) -> OllamaClient:
        """Get Ollama client for specific model (returns unavailable client if not running)"""
        if model is None:
            model = self.default_model
        
        if model not in self.clients:
            self.clients[model] = OllamaClient(self.base_url, model)
        
        return self.clients[model]
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        return self.available
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            "base_url": self.base_url,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "available": self.available,
            "loaded_models": list(self.clients.keys())
        }
    
    def update_config(self, url: str = None, model: str = None) -> Dict[str, Any]:
        """Update Ollama configuration dynamically"""
        if url is not None:
            self.base_url = url
            # Clear cached clients as URL changed
            self.clients.clear()
        
        if model is not None:
            self.default_model = model
            self.fallback_model = model
        
        # Re-check availability with new config
        client = OllamaClient(self.base_url, self.default_model)
        self.clients[self.default_model] = client
        self.available = client.available
        
        return {
            "status": "ok",
            "config": self.get_config()
        }
    
    async def generate_with_fallback(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate with automatic fallback to alternative model"""
        # Try default model first
        client = self.get_client(self.default_model)
        result = await client.generate(prompt, **kwargs)
        
        if result["status"] == "ok":
            return result
        
        # Fallback to alternative model
        logger.info(f"Primary model failed, trying fallback: {self.fallback_model}")
        client = self.get_client(self.fallback_model)
        return await client.generate(prompt, **kwargs)
    
    async def set_default_model(self, model: str):
        """Set default model"""
        self.default_model = model
        logger.info(f"Default model set to: {model}")
    
    def list_available_models(self) -> List[str]:
        """List available models"""
        return list(self.clients.keys())
