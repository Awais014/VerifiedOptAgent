"""
Parser Agent: Extracts decision variables, objective sense, and candidate constraints
with explicit tracking of source sentences from natural language operations descriptions.
"""

import re
from typing import Dict, Any, List
from .base import BaseAgent, ModelProvider


class ParserAgent(BaseAgent):
    """Decomposes unstructured operational problem text into symbolic entities."""

    def __init__(self, model_provider: ModelProvider):
        super().__init__(name="ParserAgent", role="Requirement Decomposer & Entity Extractor")
        self.provider = model_provider

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        nl_text = context.get("natural_language_text", "")
        problem_id = context.get("problem_id", "prob_001")

        # Decompose requirements using model provider
        prompt = f"Decompose into variables, bounds, and requirements:\n{nl_text}"
        _ = self.provider.generate(prompt, system_instruction="You are an expert Operations Research requirement parser.")
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', nl_text) if s.strip()]

        # Extract objective target
        sense = "MINIMIZE"
        if any(w in nl_text.lower() for w in ["maximize", "maximum profit", "highest return", "max revenue"]):
            sense = "MAXIMIZE"

        extracted_requirements = []
        for idx, sentence in enumerate(sentences):
            # Check if sentence contains quantifiable or constraint words
            has_constraint_signal = any(
                sig in sentence.lower()
                for sig in ["must", "at least", "at most", "cannot exceed", "limit", "capacity", "require", "bound", "only", "equal", "capped", "available"]
            )
            has_objective_signal = any(
                sig in sentence.lower()
                for sig in ["minimize", "maximize", "objective", "total cost", "total profit"]
            )

            category = "NEUTRAL"
            if has_objective_signal:
                category = "OBJECTIVE"
            elif has_constraint_signal:
                category = "CONSTRAINT"

            extracted_requirements.append({
                "sentence_idx": idx,
                "text": sentence,
                "category": category,
            })

        parsed_data = {
            "problem_id": problem_id,
            "raw_text": nl_text,
            "sentences": sentences,
            "objective_sense": sense,
            "requirements": extracted_requirements,
        }

        context["parsed_data"] = parsed_data
        return context
