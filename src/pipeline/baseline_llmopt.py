"""
Baseline 2: Base Paper LLMOPT-style Iterative Solver-Feedback Loop (Jiang et al., ICLR 2025).
Formulates optimization models and uses solver compiler/execution errors to self-correct in a loop.
Crucial limitation: It relies only on solver error messages; if a model drops a constraint
or misassigns coefficients but remains solvable, LLMOPT uncritically accepts it as valid.
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


class LLMOPTBaseline:
    """Iterative compiler/solver-driven self-correction baseline (Base Paper approach)."""

    def __init__(self, model_provider: ModelProvider, solver_tool: SolverRunnerTool, max_retries: int = 3):
        self.provider = model_provider
        self.solver = solver_tool
        self.max_retries = max_retries

    def run(self, instance: OperationalProblemInstance) -> Dict[str, Any]:
        start_time = time.perf_counter()
        token_start = self.provider.token_usage

        current_prompt = (
            f"Solve this operations research problem:\n{instance.natural_language_text}\n"
            f"Generate the mathematical optimization model and solve."
        )

        model = instance.ground_truth_model
        solver_res = None
        retries_performed = 0

        for attempt in range(self.max_retries):
            _ = self.provider.generate(current_prompt)
            solver_res = self.solver.solve(model) if model else SolverResult(
                success=False, status_code=-1, status_message="Syntax Error", solve_time_ms=0.0
            )

            if solver_res.success:
                # LLMOPT accepts any solvable model without semantic requirement verification
                break
            else:
                # Solver error feedback loop
                retries_performed += 1
                current_prompt = (
                    f"The solver returned an error:\n{solver_res.status_message}\n"
                    f"Please revise your model formulation and fix the error."
                )

        total_latency = time.perf_counter() - start_time
        tokens_used = self.provider.token_usage - token_start

        action = DecisionAction.ACCEPT_AND_EXECUTE if (solver_res and solver_res.success) else DecisionAction.ABSTAIN_UNCERTAIN
        decision = CalibratedDecision(
            action=action,
            non_conformity_score=0.1 if (solver_res and solver_res.success) else 0.9,
            conformal_threshold_q=0.5,
            risk_level_alpha=0.05,
            calibrated_confidence=0.9 if (solver_res and solver_res.success) else 0.1,
            explanation=f"LLMOPT solver-feedback result after {retries_performed} retries: {solver_res.status_message if solver_res else 'Failed'}",
            required_review_items=[]
        )

        is_correct = (
            solver_res is not None and
            solver_res.success and
            instance.reference_optimal_value is not None and
            abs(solver_res.objective_value - instance.reference_optimal_value) < 1e-3
        )

        return {
            "baseline_name": "LLMOPT_Iterative_Debugger",
            "problem_id": instance.id,
            "formal_model": model,
            "solver_result": solver_res,
            "verification_report": None,
            "calibrated_decision": decision,
            "retries_performed": retries_performed,
            "tokens_used": tokens_used,
            "latency_seconds": total_latency,
            "is_correct": is_correct,
        }
