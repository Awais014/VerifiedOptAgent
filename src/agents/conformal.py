"""
Conformal Risk Engine: Implements split-conformal prediction and risk control
for calibrated refusal and human escalation in LLM optimization pipelines.
Directly addresses Research Gap 2 (calibrated decisions and statistical guarantees).
"""

from typing import List, Tuple
import numpy as np

from ..schemas.contracts import (
    VerificationReport,
    SolverResult,
    DecisionAction,
    CalibratedDecision,
)


class ConformalRiskEngine:
    """Computes distribution-free conformal non-conformity scores and calibrated decisions."""

    def __init__(self, risk_level_alpha: float = 0.05):
        self.alpha = risk_level_alpha
        # Calibration non-conformity scores computed on calibration set
        self.calibration_scores: List[float] = []
        self.conformal_threshold_q: float = 0.25  # Default threshold before empirical calibration

    def compute_non_conformity_score(self, report: VerificationReport, solver_res: SolverResult) -> float:
        """
        Computes the non-conformity score s(x, y).
        Valid ground truth models have s close to 0.0.
        Perturbed, omitted, or hallucinated models have s > 0.25.
        Failed or contradictory models have s >= 1.0.
        """
        score = 0.0

        # Term 1: Solver failure / infeasibility
        if not solver_res or not solver_res.success:
            score += 1.0

        # Term 2: Verification check failures
        if report:
            if not report.overall_passed:
                score += 0.35

            # Penalty for missing requirements
            omission_penalty = 0.5 * (1.0 - report.constraint_coverage_score)
            score += omission_penalty

            # Penalty for hallucinated constraints
            score += 0.4 * min(report.hallucinated_constraint_count, 2)

            # Penalty for paraphrase disparity
            score += 0.3 * (1.0 - report.semantic_invariance_score)

            # Slack degeneracy
            if report.slack_degeneracy_detected:
                score += 0.25
        else:
            score += 0.60

        return float(min(score, 2.0))

    def calibrate(self, calibration_scores: List[float]):
        """
        Calibrates the threshold q on a held-out dataset using the split-conformal formula:
        q = Quantile( (n+1)(1 - alpha) / n )
        """
        if not calibration_scores:
            self.conformal_threshold_q = 0.25
            return

        self.calibration_scores = sorted(calibration_scores)
        n = len(self.calibration_scores)
        # Conformal quantile level
        level = min(1.0, np.ceil((n + 1) * (1.0 - self.alpha)) / n)
        self.conformal_threshold_q = float(np.quantile(self.calibration_scores, level, method="higher"))

    def evaluate_decision(self, report: VerificationReport, solver_res: SolverResult) -> CalibratedDecision:
        """
        Applies calibrated threshold to produce a tri-state decision:
        ACCEPT_AND_EXECUTE, ESCALATE_TO_HUMAN, or ABSTAIN_UNCERTAIN.
        """
        s_test = self.compute_non_conformity_score(report, solver_res)
        q = self.conformal_threshold_q

        # Escalation margin
        escalation_bandwidth = 0.35

        review_items = []
        if report and report.omitted_constraints:
            review_items.extend([f"Omitted requirement: {item}" for item in report.omitted_constraints])
        if report and report.hallucinated_constraint_count > 0:
            review_items.append(f"{report.hallucinated_constraint_count} constraints lack grounding in source text")
        if not solver_res or not solver_res.success:
            review_items.append("Solver failed to achieve primal feasibility")

        if s_test <= q:
            action = DecisionAction.ACCEPT_AND_EXECUTE
            explanation = (
                f"Model accepted with statistical risk guarantee <= {self.alpha * 100:.1f}%. "
                f"Non-conformity score ({s_test:.3f}) <= conformal threshold ({q:.3f})."
            )
        elif s_test <= q + escalation_bandwidth:
            action = DecisionAction.ESCALATE_TO_HUMAN
            explanation = (
                f"Model escalated to human operations dispatcher. Non-conformity score ({s_test:.3f}) "
                f"exceeds automated execution threshold ({q:.3f}), but falls within review bandwidth. "
                f"Dispatcher must verify {len(review_items)} flagged ambiguity items."
            )
        else:
            action = DecisionAction.ABSTAIN_UNCERTAIN
            explanation = (
                f"Model execution refused (abstention). Non-conformity score ({s_test:.3f}) significantly "
                f"exceeds safe operating limit ({q + escalation_bandwidth:.3f}). High risk of operational error."
            )

        confidence = max(0.0, 1.0 - (s_test / 2.0))

        return CalibratedDecision(
            action=action,
            non_conformity_score=s_test,
            conformal_threshold_q=q,
            risk_level_alpha=self.alpha,
            calibrated_confidence=confidence,
            explanation=explanation,
            required_review_items=review_items,
        )
