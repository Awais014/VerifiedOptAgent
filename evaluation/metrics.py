"""
Evaluation Metrics for Verified Optimization Systems.
Calculates Formulation Accuracy, Constraint Coverage Rate (CCR),
Hallucinated Constraint Rate (HCR), Semantic Invariance Score (SIS),
and Conformal Risk / Refusal rates across baselines.
"""

from typing import List, Dict, Any
import numpy as np


class OptimizationEvaluationMetrics:
    """Aggregates and computes comparative research metrics across pipeline runs."""

    @staticmethod
    def aggregate(run_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not run_records:
            return {}

        n = len(run_records)
        accuracy_count = sum(1 for r in run_records if r.get("is_correct", False))
        safe_calibrated_count = sum(1 for r in run_records if r.get("is_safely_calibrated", True))

        # Metrics for runs having verification reports
        ccr_list = []
        hcr_list = []
        sis_list = []
        for r in run_records:
            v_rep = r.get("verification_report")
            if v_rep:
                ccr_list.append(v_rep.constraint_coverage_score)
                hcr_list.append(1.0 if v_rep.hallucinated_constraint_count > 0 else 0.0)
                sis_list.append(v_rep.semantic_invariance_score)

        avg_ccr = float(np.mean(ccr_list)) if ccr_list else 0.0
        avg_hcr = float(np.mean(hcr_list)) if hcr_list else 0.0
        avg_sis = float(np.mean(sis_list)) if sis_list else 0.0

        # Conformal decision breakdown
        action_counts = {"ACCEPT_AND_EXECUTE": 0, "ESCALATE_TO_HUMAN": 0, "ABSTAIN_UNCERTAIN": 0}
        accepted_but_wrong = 0

        for r in run_records:
            dec = r.get("calibrated_decision")
            if dec:
                act_str = dec.action.value if hasattr(dec.action, "value") else str(dec.action)
                action_counts[act_str] = action_counts.get(act_str, 0) + 1
                if act_str == "ACCEPT_AND_EXECUTE" and not r.get("is_correct", False):
                    accepted_but_wrong += 1

        total_accepted = max(action_counts.get("ACCEPT_AND_EXECUTE", 0), 1)
        empirical_error_rate = accepted_but_wrong / total_accepted

        # Compute & Resource metrics
        avg_tokens = float(np.mean([r.get("tokens_used", 0) for r in run_records]))
        avg_latency = float(np.mean([r.get("latency_seconds", 0.0) for r in run_records]))

        return {
            "num_evaluated": n,
            "formulation_accuracy": (accuracy_count / n) * 100.0,
            "safety_calibration_rate": (safe_calibrated_count / n) * 100.0,
            "avg_constraint_coverage_rate": avg_ccr * 100.0,
            "avg_hallucinated_constraint_rate": avg_hcr * 100.0,
            "avg_semantic_invariance_score": avg_sis * 100.0,
            "empirical_accepted_error_rate": empirical_error_rate * 100.0,
            "decisions": action_counts,
            "avg_tokens_per_instance": avg_tokens,
            "avg_latency_seconds": avg_latency,
            "compute_normalized_accuracy": (accuracy_count / max(avg_tokens, 1.0)) * 10000.0,
        }
