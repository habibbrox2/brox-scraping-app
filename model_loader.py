"""
OpenRouter Free Model Loader
Loads models remotely from OpenRouter API
"""

import requests
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

from app.utils.logger import get_logger

# ======================
# OpenRouter API
# ======================

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# ======================
# Model Classes
# ======================

@dataclass
class Model:
    """AI Model"""
    id: str
    name: str
    provider: str
    description: str
    pricing: Dict = None
    free: bool = False

# ======================
# Free Models (No API Key)
# ======================

FREE_MODELS = [
    # Google (Free Tier)
    Model(
        id="google/gemini-flash-1.5",
        name="Gemini Flash 1.5",
        provider="Google",
        description="Fast AI model with vision support",
        free=True
    ),
    # Meta (Free)
    Model(
        id="meta-llama/llama-3.1-8b-instruct",
        name="Llama 3.1 8B",
        provider="Meta",
        description="Open source instruction model",
        free=True
    ),
    Model(
        id="meta-llama/llama-3.2-1b-instruct",
        name="Llama 3.2 1B",
        provider="Meta",
        description="Lightweight instruction model",
        free=True
    ),
    Model(
        id="meta-llama/llama-3.2-3b-instruct",
        name="Llama 3.2 3B",
        provider="Meta",
        description="Medium instruction model",
        free=True
    ),
    # Mistral (Free)
    Model(
        id="mistralai/mistral-7b-instruct",
        name="Mistral 7B",
        provider="Mistral",
        description="Fast open source model",
        free=True
    ),
    Model(
        id="mistralai/mixtral-8x7b-instruct",
        name="Mixtral 8x7B",
        provider="Mistral",
        description="Mixture of experts model",
        free=True
    ),
    # Qwen (Free)
    Model(
        id="qwen/qwen-2-7b-instruct",
        name="Qwen 2 7B",
        provider="Qwen",
        description="Alibaba's model",
        free=True
    ),
    # Phi (Free)
    Model(
        id="microsoft/phi-3-mini-128k-instruct",
        name="Phi-3 Mini",
        provider="Microsoft",
        description="Small efficient model",
        free=True
    ),
    # Google (Free)
    Model(
        id="google/gemma-2-9b-it",
        name="Gemma 2 9B",
        provider="Google",
        description="Google's open model",
        free=True
    ),
]

# ======================
# Model Loader
# ======================

class ModelLoader:
    """Load AI models remotely"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = OPENROUTER_BASE
        self.logger = get_logger()
    
    def list_free_models(self) -> List[Model]:
        """List all free models"""
        return FREE_MODELS
    
    def list_by_provider(self, provider: str) -> List[Model]:
        """Filter by provider"""
        return [m for m in FREE_MODELS if m.provider.lower() == provider.lower()]
    
    def get_model(self, model_id: str) -> Optional[Model]:
        """Get specific model"""
        for m in FREE_MODELS:
            if m.id == model_id:
                return m
        return None
    
    def fetch_models_from_api(self) -> List[Dict]:
        """Fetch available models from OpenRouter API"""
        if not self.api_key:
            return []
        
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            self.logger.error(f"Failed to fetch models from API: {e}")
            pass
        
        return []
    
    def get_free_completion(self, prompt: str, model_id: str = None) -> Dict:
        """Get completion using free model (no API key needed for some)"""
        model_id = model_id or "google/gemini-flash-1.5"
        
        # For truly free models, we can try without key
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key if available
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "model": model_id,
                    "success": True
                }
            else:
                return {
                    "error": f"Status {resp.status_code}",
                    "response": resp.text,
                    "model": model_id
                }
        
        except Exception as e:
            return {"error": str(e)}

# ======================
# Chat Interface
# ======================

class AIChat:
    """Simple AI chat interface"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.loader = ModelLoader(api_key)
        self.model = model or "google/gemini-flash-1.5"
    
    def chat(self, message: str) -> str:
        """Send chat message"""
        result = self.loader.get_free_completion(message, self.model)
        
        if result.get("success"):
            return result["response"]
        elif result.get("error"):
            return f"Error: {result['error']}"
        
        return "Failed to get response"
    
    def summarize(self, text: str) -> str:
        """Summarize text"""
        prompt = f"Summarize this in 2 sentences:\n\n{text}"
        return self.chat(prompt)
    
    def extract_entities(self, text: str, entity_type: str = "important") -> str:
        """Extract entities"""
        prompt = f"Extract all {entity_type} entities from this text:\n\n{text}"
        return self.chat(prompt)

# ======================
# Main
# ======================

def main():
    print("=" * 50)
    print("OpenRouter Free Model Loader")
    print("=" * 50)
    
    loader = ModelLoader()
    
    # List models
    print("\nFree Models:")
    print("-" * 30)
    
    for m in loader.list_free_models():
        print(f"• {m.name} ({m.provider})")
        print(f"  ID: {m.id}")
    
    # Test chat
    print("\n" + "=" * 50)
    print("Testing Chat:")
    print("-" * 30)
    
    chat = AIChat()
    
    # Try each model
    models_to_test = [
        "google/gemini-flash-1.5",
        "meta-llama/llama-3.2-1b-instruct"
    ]
    
    for model_id in models_to_test:
        print(f"\n[{model_id}]")
        chat.model = model_id
        
        try:
            resp = chat.chat("What is AI? (answer in 1 sentence)")
            print(f"Response: {resp[:100]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()