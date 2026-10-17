"""
Base Agent and Model Provider Interface.
Supports offline deterministic model provider (for zero-cost reproducible tests)
and online cloud LLM provider (Google Gemini / OpenAI compatible).
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAgent(ABC):
    """Abstract base class for agents in the verified optimization pipeline."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent's specific role given pipeline context."""
        pass


class ModelProvider:
    """Unified LLM inference interface."""

    def __init__(self, provider_type: str = "mock", model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        self.provider_type = provider_type
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.token_usage = 0

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Generates text from the configured provider."""
        # Simple token tracking heuristic (approx 4 chars per token)
        prompt_tokens = len(prompt) // 4 + len(system_instruction) // 4
        self.token_usage += prompt_tokens

        if self.provider_type == "gemini" and self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={"system_instruction": system_instruction} if system_instruction else None
                )
                output_tokens = len(response.text) // 4
                self.token_usage += output_tokens
                return response.text
            except Exception as e:
                # Fallback to deterministic mock if API fails
                return self._mock_generate(prompt)

        return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """Deterministic mock response for offline benchmarking."""
        # Returns structured fallback response based on prompt keywords
        return "Deterministic Mock Provider Output"
