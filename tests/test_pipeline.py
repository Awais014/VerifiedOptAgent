"""
Unit and Integration Tests for Verified Optimization Pipeline.
Compatible with standard library unittest and pytest.
"""

import unittest
import numpy as np
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schemas.contracts import (
    Variable,
    VariableType,
    LinearConstraint,
    ConstraintSense,
    ObjectiveFunction,
    OptimizationSense,
    FormalOptimizationModel,
    DecisionAction,
)
from src.tools.solver_runner import SolverRunnerTool
from src.tools.paraphraser import SemanticParaphraserTool
from src.agents.conformal import ConformalRiskEngine


class TestVerifiedPipeline(unittest.TestCase):

    def test_highs_solver_lp(self):
        """Test HiGHS solver on simple 2D LP."""
        solver = SolverRunnerTool()
        v1 = Variable(name="x1", var_type=VariableType.CONTINUOUS, lower_bound=0.0)
        v2 = Variable(name="x2", var_type=VariableType.CONTINUOUS, lower_bound=0.0)

        # Maximize 3x1 + 2x2 subject to x1 + x2 <= 4, x1 <= 2
        obj = ObjectiveFunction(sense=OptimizationSense.MAXIMIZE, coefficients={"x1": 3.0, "x2": 2.0})
        c1 = LinearConstraint(name="c1", coefficients={"x1": 1.0, "x2": 1.0}, sense=ConstraintSense.LEQ, rhs=4.0)
        c2 = LinearConstraint(name="c2", coefficients={"x1": 1.0}, sense=ConstraintSense.LEQ, rhs=2.0)

        model = FormalOptimizationModel(
            problem_id="T_01",
            problem_name="Test LP",
            problem_type="LP",
            variables=[v1, v2],
            objective=obj,
            constraints=[c1, c2],
        )

        res = solver.solve(model)
        self.assertTrue(res.success)
        self.assertTrue(np.isclose(res.objective_value, 10.0))
        self.assertTrue(np.isclose(res.variable_values["x1"], 2.0))
        self.assertTrue(np.isclose(res.variable_values["x2"], 2.0))

    def test_highs_solver_milp(self):
        """Test HiGHS solver on Integer Programming problem."""
        solver = SolverRunnerTool()
        v1 = Variable(name="y1", var_type=VariableType.INTEGER, lower_bound=0.0)
        v2 = Variable(name="y2", var_type=VariableType.INTEGER, lower_bound=0.0)

        # Maximize 5y1 + 4y2 subject to 2y1 + y2 <= 9, y1 + 3y2 <= 11
        obj = ObjectiveFunction(sense=OptimizationSense.MAXIMIZE, coefficients={"y1": 5.0, "y2": 4.0})
        c1 = LinearConstraint(name="c1", coefficients={"y1": 2.0, "y2": 1.0}, sense=ConstraintSense.LEQ, rhs=9.0)
        c2 = LinearConstraint(name="c2", coefficients={"y1": 1.0, "y2": 3.0}, sense=ConstraintSense.LEQ, rhs=11.0)

        model = FormalOptimizationModel(
            problem_id="T_02",
            problem_name="Test MILP",
            problem_type="MILP",
            variables=[v1, v2],
            objective=obj,
            constraints=[c1, c2],
        )

        res = solver.solve(model)
        self.assertTrue(res.success)
        self.assertTrue(float(res.variable_values["y1"]).is_integer())
        self.assertTrue(float(res.variable_values["y2"]).is_integer())

    def test_paraphraser_invariance(self):
        """Test semantic paraphraser tool."""
        paraphraser = SemanticParaphraserTool()
        text = "The operations team must maximize profit and cost must not exceed 500."
        variants = paraphraser.generate_paraphrases(text, 2)
        self.assertEqual(len(variants), 2)
        self.assertNotEqual(variants[0], text)

    def test_conformal_risk_bounds(self):
        """Test conformal risk engine thresholding and decision bounds."""
        conformal = ConformalRiskEngine(risk_level_alpha=0.05)
        calib = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.12]
        conformal.calibrate(calib)
        self.assertLessEqual(conformal.conformal_threshold_q, 0.15)


if __name__ == "__main__":
    unittest.main()
