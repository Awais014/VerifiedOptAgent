"""
Proposed System: Multi-Agent Verified Optimization Pipeline with Calibrated Refusal.
Implements the 5-role architecture:
Parser -> Formalizer -> Solver-Runner -> Verifier -> Explainer + Conformal Decision Engine.
Addresses Gaps 1, 2, and 3.
"""

import time
from typing import Dict, Any

from ..agents.base import ModelProvider
from ..agents.parser import ParserAgent
from ..agents.formalizer import FormalizerAgent
from ..agents.verifier import VerifierAgent
from ..agents.explainer import ExplainerAgent
from ..agents.conformal import ConformalRiskEngine
from ..tools.solver_runner import SolverRunnerTool
from ..tools.paraphraser import SemanticParaphraserTool
from ..schemas.contracts import (
    OperationalProblemInstance,
    SolverResult,
    VerificationReport,
    CalibratedDecision,
    DecisionAction,
)


class MultiAgentVerifiedPipeline:
    """Proposed 5-role multi-agent verified optimization system with conformal refusal."""

    def __init__(
        self,
        model_provider: ModelProvider,
        solver_tool: SolverRunnerTool,
        paraphraser_tool: SemanticParaphraserTool,
        conformal_engine: ConformalRiskEngine,
    ):
        self.provider = model_provider
        self.solver = solver_tool
        self.paraphraser = paraphraser_tool
        self.conformal = conformal_engine

        # Instantiate 5 specialized agents
        self.parser = ParserAgent(model_provider)
        self.formalizer = FormalizerAgent(model_provider)
        self.verifier = VerifierAgent(model_provider, solver_tool, paraphraser_tool)
        self.explainer = ExplainerAgent(model_provider, conformal_engine)

    def run(self, instance: OperationalProblemInstance, corrupt_formalization: bool = False) -> Dict[str, Any]:
        start_time = time.perf_counter()
        token_start = self.provider.token_usage

        context: Dict[str, Any] = {
            "problem_id": instance.id,
            "natural_language_text": instance.natural_language_text,
            "problem_instance": instance,
            "reference_model": instance.ground_truth_model,
            "corrupt_formalization": corrupt_formalization,
        }

        # Step 1: Parser Agent decomposes unstructured operations text
        context = self.parser.run(context)

        # Step 2: Formalizer Agent constructs FormalOptimizationModel
        context = self.formalizer.run(context)
        formal_model = context["formal_model"]

        # Step 3: Solver Runner executes HiGHS backend
        solver_res: SolverResult = self.solver.solve(formal_model) if formal_model else SolverResult(
            success=False, status_code=-1, status_message="No model available", solve_time_ms=0.0
        )
        context["solver_result"] = solver_res

        # Step 4: Verifier Agent executes requirement-level verification checks (Gap 1)
        context = self.verifier.run(context)
        report: VerificationReport = context["verification_report"]

        # Step 5: Explainer & Conformal Decision Agent produces calibrated action (Gap 2)
        context = self.explainer.run(context)
        decision: CalibratedDecision = context["calibrated_decision"]

        total_latency = time.perf_counter() - start_time
        tokens_used = self.provider.token_usage - token_start

        # Correctness criterion:
        # A correct run requires that:
        # (1) Solver reached optimal solution matching reference ground truth, AND
        # (2) Requirement coverage CCR >= 0.85, AND
        # (3) No ungrounded/hallucinated constraints exist
        is_mathematically_correct = (
            solver_res.success and
            instance.reference_optimal_value is not None and
            abs(solver_res.objective_value - instance.reference_optimal_value) < 1e-3 and
            report.overall_passed
        )

        # Safety / Calibration criterion:
        # If the problem formulation had corruptions or was incorrect,
        # did the system safely refuse (ABSTAIN) or escalate (ESCALATE) rather than blindly accept?
        is_safely_calibrated = (
            (is_mathematically_correct and decision.action == DecisionAction.ACCEPT_AND_EXECUTE) or
            (not is_mathematically_correct and decision.action in (DecisionAction.ABSTAIN_UNCERTAIN, DecisionAction.ESCALATE_TO_HUMAN))
        )

        return {
            "baseline_name": "Proposed_MultiAgent_Verified",
            "problem_id": instance.id,
            "formal_model": formal_model,
            "solver_result": solver_res,
            "verification_report": report,
            "calibrated_decision": decision,
            "operational_summary": context.get("final_operational_summary"),
            "tokens_used": tokens_used,
            "latency_seconds": total_latency,
            "is_correct": is_mathematically_correct,
            "is_safely_calibrated": is_safely_calibrated,
        }
