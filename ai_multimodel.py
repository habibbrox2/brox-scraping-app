"""
AI Multi-Model System with Tools Calling
Supports: OpenAI, Anthropic, Google, Meta, and custom tools
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# ======================
# Model Configuration
# ======================

class Model(Enum):
    # OpenAI
    GPT_4O = "openai/gpt-4o"
    GPT_4O_MINI = "openai/gpt-4o-mini"
    GPT_4_TURBO = "openai/gpt-4-turbo"
    
    # Anthropic
    CLAUDE_3_OPUS = "anthropic/claude-3-opus-20240229"
    CLAUDE_3_SONNET = "anthropic/claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "anthropic/claude-3-haiku-20240307"
    
    # Google
    GEMINI_PRO = "google/gemini-pro"
    GEMINI_FLASH = "google/gemini-flash-1.5"
    
    # Meta
    LLAMA_3_70B = "meta-llama/llama-3-70b-instruct"
    LLAMA_3_8B = "meta-llama/llama-3-8b-instruct"
    
    # Mistral
    MISTRAL_7B = "mistralai/mistral-7b-instruct"
    MIXTRAL_8X7B = "mistralai/mixtral-8x7b-instruct"

# ======================
# Tool System
# ======================

@dataclass
class Tool:
    """Represents a callable tool"""
    name: str
    description: str
    parameters: Dict
    
    def to_openai(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolExecutor:
    """Execute tools based on AI responses"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools"""
        
        # Search tool
        self.register("search", "Search the web for information", {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }, self._search_tool)
        
        # Analyze tool
        self.register("analyze_data", "Analyze and summarize data", {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to analyze"}
            },
            "required": ["data"]
        }, self._analyze_tool)
        
        # Extract tool
        self.register("extract_entities", "Extract entities from text", {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to extract from"},
                "entity_type": {"type": "string", "description": "Type: person/org/location"}
            },
            "required": ["text"]
        }, self._extract_tool)
        
        # Translate tool
        self.register("translate", "Translate text between languages", {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate"},
                "target_lang": {"type": "string", "description": "Target language"}
            },
            "required": ["text", "target_lang"]
        }, self._translate_tool)
    
    def register(self, name: str, desc: str, params: Dict, func: Callable):
        """Register a tool"""
        self.tools[name] = {
            "description": desc,
            "parameters": params,
            "function": func
        }
    
    def execute(self, name: str, args: Dict) -> Any:
        """Execute a tool"""
        if name in self.tools:
            return self.tools[name]["function"](**args)
        return {"error": f"Tool {name} not found"}
    
    def _search_tool(self, query: str) -> Dict:
        """Web search tool"""
        return {"query": query, "results": "Search executed for: " + query}
    
    def _analyze_tool(self, data: str) -> Dict:
        """Analyze data"""
        return {
            "summary": f"Data analysis: {len(data)} characters",
            "sentiment": "neutral",
            "key_points": ["Point 1", "Point 2"]
        }
    
    def _extract_tool(self, text: str, entity_type: str = "person") -> Dict:
        """Extract entities"""
        return {
            "entities": ["Entity1", "Entity2"],
            "type": entity_type,
            "count": 2
        }
    
    def _translate_tool(self, text: str, target_lang: str) -> Dict:
        """Translate"""
        return {
            "original": text,
            "translated": f"[{target_lang}] {text}",
            "language": target_lang
        }
    
    def get_tools_schema(self) -> List[Dict]:
        """Get OpenAI format tools schema"""
        return [
            Tool(t["description"], t["description"], t["parameters"]).to_openai()
            for t in self.tools.values()
        ]

# ======================
# Multi-Model AI
# ======================

class AIMultiModel:
    """Multi-model AI with tool calling"""
    
    def __init__(self, api_key: str, default_model: str = None):
        self.api_key = api_key
        self.default_model = default_model or Model.GPT_4O_MINI.value
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.executor = ToolExecutor()
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://scrapmaster.local",
            "X-Title": "ScrapMaster AI"
        }
    
    def chat(self, message: str, model: str = None, tools: bool = False) -> Dict:
        """Chat with AI"""
        model = model or self.default_model
        
        messages = [{"role": "user", "content": message}]
        
        # Tools
        tools_param = None
        if tools:
            tools_param = self.executor.get_tools_schema()
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools_param,
            "max_tokens": 2000
        }
        
        try:
            resp = requests.post(
                self.base_url,
                json=payload,
                headers=self._get_headers(),
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                # Check for tool calls
                if result["choices"][0]["message"].get("tool_calls"):
                    tool_calls = result["choices"][0]["message"]["tool_calls"]
                    results = []
                    
                    for tc in tool_calls:
                        name = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
                        result = self.executor.execute(name, args)
                        results.append({
                            "tool": name,
                            "result": result
                        })
                    
                    return {
                        "response": result["choices"][0]["message"]["content"],
                        "tool_results": results
                    }
                
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "model": model
                }
        
        except Exception as e:
            return {"error": str(e)}
    
    def enhance_data(self, data: List[Dict], model: str = None) -> List[Dict]:
        """Enhance scraped data with AI"""
        model = model or self.default_model
        
        # Build prompt
        items_str = "\n".join([
            f"- {d.get('title', d.get('link', ''))}"
            for d in data[:10]
        ])
        
        prompt = f"""Analyze these news items and add metadata:

Items:
{items_str}

For each item, output JSON with:
- title
- category (news/tech/business/sports/entertainment)
- sentiment (positive/negative/neutral)
- summary (1 sentence)

Output as JSON array:"""
        
        result = self.chat(prompt, model)
        
        if "response" in result:
            try:
                # Parse JSON
                content = result["response"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                return json.loads(content)
            except:
                pass
        
        return data

# ======================
# Usage Examples
# ======================

def main():
    import sys
    
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    
    if not api_key:
        print("Set OPENROUTER_API_KEY environment variable")
        return
    
    # Initialize
    ai = AIMultiModel(api_key)
    
    # Example 1: Simple chat
    print("=" * 40)
    print("1. Simple Chat")
    print("=" * 40)
    result = ai.chat("What is the capital of France?")
    print(result.get("response", ""))
    
    # Example 2: With tools
    print("\n" + "=" * 40)
    print("2. With Tools")
    print("=" * 40)
    result = ai.chat(
        "Extract all person names from: John works at Google in New York",
        tools=True
    )
    print(result.get("response", ""))
    
    # Example 3: Different models
    print("\n" + "=" * 40)
    print("3. Different Models")
    print("=" * 40)
    
    models = [
        Model.GPT_4O_MINI.value,
        Model.LLAMA_3_8B.value,
        Model.GEMINI_FLASH.value
    ]
    
    for m in models:
        r = ai.chat("Hello!", model=m)
        print(f"{m}: {r.get('response', r.get('error', ''))[:50]}...")

if __name__ == "__main__":
    main()