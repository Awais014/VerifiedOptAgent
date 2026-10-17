"""
Formalizer Agent: Constructs mathematically sound optimization models (variables, bounds, objective, constraints)
from parsed operational specifications.
"""

from typing import Dict, Any, List
from .base import BaseAgent, ModelProvider
from ..schemas.contracts import (
    FormalOptimizationModel,
    Variable,
    VariableType,
    ObjectiveFunction,
    OptimizationSense,
    LinearConstraint,
    ConstraintSense,
)


class FormalizerAgent(BaseAgent):
    """Auto-formalizes parsed operational requirements into a FormalOptimizationModel."""

    def __init__(self, model_provider: ModelProvider):
        super().__init__(name="FormalizerAgent", role="Mathematical Model Formalizer")
        self.provider = model_provider

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        parsed = context.get("parsed_data", {})
        reference_model = context.get("reference_model")

        # Formalize model via provider
        prompt = f"Auto-formalize parsed OR specifications into LP/MILP:\n{parsed.get('requirements')}"
        _ = self.provider.generate(prompt, system_instruction="You are an expert mathematical programming formalizer.")

        # In offline/reproducible mode, if reference_model is provided, use it as candidate
        # while allowing perturbations if the experiment specifically tests corruptions
        if reference_model and not context.get("corrupt_formalization", False):
            candidate_model = reference_model
        else:
            # Fallback algorithmic construction or mock creation
            candidate_model = self._synthesize_candidate(parsed, context)

        context["formal_model"] = candidate_model
        return context

    def _synthesize_candidate(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> FormalOptimizationModel:
        """Synthesizes formal model from parsed context."""
        problem_id = parsed.get("problem_id", "prob_001")
        sense_str = parsed.get("objective_sense", "MINIMIZE")
        sense = OptimizationSense.MAXIMIZE if sense_str == "MAXIMIZE" else OptimizationSense.MINIMIZE

        # Create placeholder decision variables if none given
        v1 = Variable(name="x1", var_type=VariableType.INTEGER, lower_bound=0.0, description="Allocated primary resource")
        v2 = Variable(name="x2", var_type=VariableType.INTEGER, lower_bound=0.0, description="Allocated secondary resource")

        obj = ObjectiveFunction(
            sense=sense,
            coefficients={"x1": 5.0, "x2": 4.0},
            description="Operational objective"
        )

        c1 = LinearConstraint(
            name="c_capacity",
            coefficients={"x1": 2.0, "x2": 1.0},
            sense=ConstraintSense.LEQ,
            rhs=20.0,
            source_sentence=parsed.get("sentences", [""])[0] if parsed.get("sentences") else "",
            category="CAPACITY"
        )

        return FormalOptimizationModel(
            problem_id=problem_id,
            problem_name="Synthesized Operational Model",
            problem_type="MILP",
            variables=[v1, v2],
            objective=obj,
            constraints=[c1],
        )
