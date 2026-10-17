"""
Explainer Agent: Synthesizes final decision and actionable operational explanations
for human operations dispatchers and decision makers.
"""

from typing import Dict, Any
from .base import BaseAgent, ModelProvider
from .conformal import ConformalRiskEngine
from ..schemas.contracts import (
    SolverResult,
    VerificationReport,
    CalibratedDecision,
    FormalOptimizationModel,
)


class ExplainerAgent(BaseAgent):
    """Generates transparent, audit-ready operational explanations and calibrated decisions."""

    def __init__(self, model_provider: ModelProvider, conformal_engine: ConformalRiskEngine):
        super().__init__(name="ExplainerAgent", role="Operational Explainer & Decision Dispatcher")
        self.provider = model_provider
        self.conformal_engine = conformal_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        solver_res: SolverResult = context.get("solver_result")
        report: VerificationReport = context.get("verification_report")
        formal_model: FormalOptimizationModel = context.get("formal_model")

        # Generate operational summary via provider
        _ = self.provider.generate(
            f"Generate operational audit summary for dispatcher:\nSolver: {solver_res.status_message if solver_res else 'None'}",
            system_instruction="You are an operations dispatch explainer."
        )

        # Evaluate calibrated decision
        decision: CalibratedDecision = self.conformal_engine.evaluate_decision(report, solver_res)
        context["calibrated_decision"] = decision

        # Build natural language explanation
        explanation_lines = []
        explanation_lines.append(f"=== OPERATIONAL DISPATCH DECISION: {decision.action.value} ===")
        explanation_lines.append(decision.explanation)

        if solver_res and solver_res.success:
            explanation_lines.append(f"\nOptimization Summary:")
            explanation_lines.append(f"- Optimal Objective Value: {solver_res.objective_value:.4f}")
            explanation_lines.append(f"- Solver Engine: {solver_res.solver_name} (Solve Time: {solver_res.solve_time_ms:.2f} ms)")
            explanation_lines.append(f"- Key Decision Allocations:")
            for var_name, val in list(solver_res.variable_values.items())[:6]:
                explanation_lines.append(f"  * {var_name}: {val:.2f}")

        if report:
            explanation_lines.append(f"\nVerification Audit:")
            explanation_lines.append(f"- Requirement Constraint Coverage: {report.constraint_coverage_score * 100:.1f}%")
            explanation_lines.append(f"- Semantic Paraphrase Invariance: {report.semantic_invariance_score * 100:.1f}%")
            explanation_lines.append(f"- Hallucinated Constraints: {report.hallucinated_constraint_count}")
            if report.omitted_constraints:
                explanation_lines.append(f"- Flagged Omitted Requirements:")
                for omit in report.omitted_constraints:
                    explanation_lines.append(f"  ! {omit}")

        if decision.required_review_items:
            explanation_lines.append(f"\nAction Required from Operations Supervisor:")
            for item in decision.required_review_items:
                explanation_lines.append(f"  [Action] {item}")

        full_explanation = "\n".join(explanation_lines)
        context["final_operational_summary"] = full_explanation
        return context
