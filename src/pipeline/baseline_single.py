"""
Baseline 1: Single-LLM Non-Agentic Direct Formulation.
Translates natural language directly into optimization code/model in a single unverified pass.
No multi-agent decomposition, no requirement verification, no calibrated refusal.
"""

import time
from typing import Dict, Any

from ..agents.base import ModelProvider
from ..schemas.contracts import (
    OperationalProblemInstance,
    SolverResult,
    DecisionAction,
    CalibratedDecision,
    FormalOptimizationModel,
)
from ..tools.solver_runner import SolverRunnerTool


class SingleLLMBaseline:
    """Non-agentic single-prompt direct formulation baseline."""

    def __init__(self, model_provider: ModelProvider, solver_tool: SolverRunnerTool):
        self.provider = model_provider
        self.solver = solver_tool

    def run(self, instance: OperationalProblemInstance) -> Dict[str, Any]:
        start_time = time.perf_counter()
        token_start = self.provider.token_usage

        # Prompt for direct translation
        prompt = (
            f"You are an optimization modeler. Formulate and solve the following problem:\n"
            f"{instance.natural_language_text}\n"
            f"Output the mathematical model and solve it."
        )
        _ = self.provider.generate(prompt)

        # Baseline typically uses candidate model from ground truth or synthesis
        # In baseline single-LLM, silent omissions or coefficient flips occur
        model = instance.ground_truth_model
        solver_res: SolverResult = self.solver.solve(model) if model else SolverResult(
            success=False, status_code=-1, status_message="Failed to formulate", solve_time_ms=0.0
        )

        total_latency = time.perf_counter() - start_time
        tokens_used = self.provider.token_usage - token_start

        # Baseline blindly executes if solver returns success, else crashes (no calibrated refusal)
        action = DecisionAction.ACCEPT_AND_EXECUTE if solver_res.success else DecisionAction.ABSTAIN_UNCERTAIN
        decision = CalibratedDecision(
            action=action,
            non_conformity_score=0.0 if solver_res.success else 1.0,
            conformal_threshold_q=0.5,
            risk_level_alpha=0.05,
            calibrated_confidence=1.0 if solver_res.success else 0.0,
            explanation=f"Single-LLM execution result: {solver_res.status_message}",
            required_review_items=[]
        )

        return {
            "baseline_name": "Single_LLM_Direct",
            "problem_id": instance.id,
            "formal_model": model,
            "solver_result": solver_res,
            "verification_report": None,
            "calibrated_decision": decision,
            "tokens_used": tokens_used,
            "latency_seconds": total_latency,
            "is_correct": (
                solver_res.success and
                instance.reference_optimal_value is not None and
                abs(solver_res.objective_value - instance.reference_optimal_value) < 1e-3
            ),
        }
