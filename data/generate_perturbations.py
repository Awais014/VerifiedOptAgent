"""
Generates the controlled perturbation and corruption test suite.
Evaluates semantic paraphrase invariance, dropped constraint detection,
and calibrated refusal under adversarial or contradictory inputs.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schemas.contracts import (
    OperationalProblemInstance,
    FormalOptimizationModel,
    LinearConstraint,
    ConstraintSense,
)


def generate_perturbations():
    bench_path = Path("VerifiedOptAgent/data/opsor_bench.json")
    with open(bench_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    test_cases = []

    for item in raw_data:
        inst = OperationalProblemInstance.model_validate(item)

        # 1. Clean Original Instance
        test_cases.append({
            "test_id": f"{inst.id}_CLEAN",
            "base_problem_id": inst.id,
            "perturbation_type": "CLEAN",
            "description": "Original ground-truth operational problem description",
            "instance": inst.model_dump(),
            "expected_outcome": "ACCEPT_AND_EXECUTE",
            "corrupt_formalization": False,
        })

        # 2. Linguistic Paraphrase Variant
        if inst.paraphrased_variants:
            p_inst = inst.model_copy(deep=True)
            p_inst.natural_language_text = inst.paraphrased_variants[0]
            test_cases.append({
                "test_id": f"{inst.id}_PARAPHRASE_1",
                "base_problem_id": inst.id,
                "perturbation_type": "PARAPHRASE",
                "description": "Semantically equivalent linguistic paraphrase",
                "instance": p_inst.model_dump(),
                "expected_outcome": "ACCEPT_AND_EXECUTE",
                "corrupt_formalization": False,
            })

        # 3. Dropped Constraint Corruption (Simulates silent omission by LLM)
        corrupted_inst = inst.model_copy(deep=True)
        if corrupted_inst.ground_truth_model and len(corrupted_inst.ground_truth_model.constraints) > 1:
            # Remove the last operational constraint
            dropped = corrupted_inst.ground_truth_model.constraints.pop()
            corrupted_inst.required_constraint_count -= 1
            test_cases.append({
                "test_id": f"{inst.id}_CORRUPT_DROPPED_CONSTRAINT",
                "base_problem_id": inst.id,
                "perturbation_type": "DROPPED_CONSTRAINT",
                "description": f"Silent omission of constraint '{dropped.name}' ({dropped.category})",
                "instance": corrupted_inst.model_dump(),
                "expected_outcome": "ESCALATE_TO_HUMAN",
                "corrupt_formalization": True,
            })

        # 4. Infeasible / Contradictory Bounds
        infeasible_inst = inst.model_copy(deep=True)
        if infeasible_inst.ground_truth_model:
            # Add an impossible contradiction: sum <= -10 for non-negative variables
            c_impossible = LinearConstraint(
                name="c_contradiction",
                coefficients={v.name: 1.0 for v in infeasible_inst.ground_truth_model.variables[:2]},
                sense=ConstraintSense.LEQ,
                rhs=-10.0,
                source_sentence="Operational budget imposes an impossible negative allocation restriction.",
                category="CONTRADICTION"
            )
            infeasible_inst.ground_truth_model.constraints.append(c_impossible)
            test_cases.append({
                "test_id": f"{inst.id}_CORRUPT_CONTRADICTORY",
                "base_problem_id": inst.id,
                "perturbation_type": "CONTRADICTION",
                "description": "Contradictory impossible operational constraint causing solver infeasibility",
                "instance": infeasible_inst.model_dump(),
                "expected_outcome": "ABSTAIN_UNCERTAIN",
                "corrupt_formalization": True,
            })

    out_path = Path("VerifiedOptAgent/data/perturbation_suite.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=2)

    print(f"Generated {len(test_cases)} comprehensive perturbation test cases at {out_path}")


if __name__ == "__main__":
    generate_perturbations()
