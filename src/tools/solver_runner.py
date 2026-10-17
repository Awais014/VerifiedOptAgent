"""
HiGHS Optimization Solver Runner Tool.
Executes mathematical optimization models (LP / MILP) using SciPy's HiGHS solver backend.
Translates structured Pydantic contracts into matrices and returns rigorous SolverResult.
"""

import time
from typing import Dict, List, Tuple
import numpy as np
from scipy import optimize as opt

from ..schemas.contracts import (
    FormalOptimizationModel,
    SolverResult,
    OptimizationSense,
    ConstraintSense,
    VariableType,
)


class SolverRunnerTool:
    """Deterministic, sandboxed solver execution wrapper for HiGHS."""

    def __init__(self, time_limit_seconds: float = 30.0):
        self.time_limit = time_limit_seconds

    def solve(self, model: FormalOptimizationModel) -> SolverResult:
        """Solves a FormalOptimizationModel and returns structured execution metrics."""
        start_time = time.perf_counter()

        # Variable index mapping
        var_names = [v.name for v in model.variables]
        var_to_idx = {name: i for i, name in enumerate(var_names)}
        n_vars = len(var_names)

        if n_vars == 0:
            return SolverResult(
                success=False,
                status_code=-1,
                status_message="Empty model: no decision variables defined",
                solve_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Objective vector c
        c = np.zeros(n_vars, dtype=np.float64)
        for var_name, coeff in model.objective.coefficients.items():
            if var_name in var_to_idx:
                c[var_to_idx[var_name]] = coeff

        # HiGHS minimizes c^T x. If MAXIMIZE, invert c
        is_maximize = model.objective.sense == OptimizationSense.MAXIMIZE
        if is_maximize:
            c_solve = -c
        else:
            c_solve = c

        # Variable bounds and integrality
        lb = np.zeros(n_vars, dtype=np.float64)
        ub = np.full(n_vars, np.inf, dtype=np.float64)
        integrality = np.zeros(n_vars, dtype=np.int32)
        has_integers = False

        for i, var in enumerate(model.variables):
            lb[i] = var.lower_bound
            if var.upper_bound is not None:
                ub[i] = var.upper_bound

            if var.var_type in (VariableType.INTEGER, VariableType.BINARY):
                integrality[i] = 1
                has_integers = True
                if var.var_type == VariableType.BINARY:
                    ub[i] = min(ub[i], 1.0)
                    lb[i] = max(lb[i], 0.0)

        # Parse constraints
        A_rows = []
        lhs_bounds = []
        rhs_bounds = []
        constraint_names = []

        for c_item in model.constraints:
            row = np.zeros(n_vars, dtype=np.float64)
            for var_name, coeff in c_item.coefficients.items():
                if var_name in var_to_idx:
                    row[var_to_idx[var_name]] = coeff
                else:
                    # Variable in constraint not declared in variables list
                    pass

            A_rows.append(row)
            constraint_names.append(c_item.name)

            if c_item.sense == ConstraintSense.LEQ:
                lhs_bounds.append(-np.inf)
                rhs_bounds.append(c_item.rhs)
            elif c_item.sense == ConstraintSense.GEQ:
                lhs_bounds.append(c_item.rhs)
                rhs_bounds.append(np.inf)
            elif c_item.sense == ConstraintSense.EQ:
                lhs_bounds.append(c_item.rhs)
                rhs_bounds.append(c_item.rhs)

        try:
            if len(A_rows) > 0:
                A = np.array(A_rows, dtype=np.float64)
                constraints = opt.LinearConstraint(A, lhs_bounds, rhs_bounds)
            else:
                constraints = None

            bounds = opt.Bounds(lb, ub)

            # Choose solver backend: opt.milp for mixed integer, opt.linprog for continuous
            if has_integers:
                res = opt.milp(
                    c=c_solve,
                    integrality=integrality,
                    bounds=bounds,
                    constraints=constraints,
                    options={"time_limit": self.time_limit},
                )
            else:
                # Use linprog with highs
                A_ub_list, b_ub_list = [], []
                A_eq_list, b_eq_list = [], []

                for row, l_val, r_val in zip(A_rows, lhs_bounds, rhs_bounds):
                    if l_val == r_val:
                        A_eq_list.append(row)
                        b_eq_list.append(r_val)
                    elif r_val < np.inf:
                        A_ub_list.append(row)
                        b_ub_list.append(r_val)
                    elif l_val > -np.inf:
                        A_ub_list.append(-row)
                        b_ub_list.append(-l_val)

                A_ub = np.array(A_ub_list) if len(A_ub_list) > 0 else None
                b_ub = np.array(b_ub_list) if len(b_ub_list) > 0 else None
                A_eq = np.array(A_eq_list) if len(A_eq_list) > 0 else None
                b_eq = np.array(b_eq_list) if len(b_eq_list) > 0 else None
                bounds_tuple = [(l, None if np.isinf(u) else u) for l, u in zip(lb, ub)]

                res = opt.linprog(
                    c=c_solve,
                    A_ub=A_ub,
                    b_ub=b_ub,
                    A_eq=A_eq,
                    b_eq=b_eq,
                    bounds=bounds_tuple,
                    method="highs",
                    options={"time_limit": self.time_limit},
                )

            solve_time_ms = (time.perf_counter() - start_time) * 1000.0

            if res.success:
                x_vals = res.x
                var_dict = {name: float(x_vals[i]) for i, name in enumerate(var_names)}
                raw_obj = float(res.fun)
                opt_val = -raw_obj if is_maximize else raw_obj
                opt_val += model.objective.constant

                # Calculate constraint slacks
                slack_dict = {}
                if len(A_rows) > 0:
                    activity = A @ x_vals
                    for name, act, l_val, r_val in zip(constraint_names, activity, lhs_bounds, rhs_bounds):
                        if r_val < np.inf and l_val == -np.inf:
                            slack_dict[name] = float(r_val - act)
                        elif l_val > -np.inf and r_val == np.inf:
                            slack_dict[name] = float(act - l_val)
                        else:
                            slack_dict[name] = float(abs(act - r_val))

                return SolverResult(
                    success=True,
                    status_code=int(res.status),
                    status_message=str(res.message),
                    objective_value=opt_val,
                    variable_values=var_dict,
                    slack_values=slack_dict,
                    solve_time_ms=solve_time_ms,
                    solver_name="HiGHS",
                )
            else:
                return SolverResult(
                    success=False,
                    status_code=int(res.status),
                    status_message=str(res.message),
                    objective_value=None,
                    variable_values={},
                    slack_values={},
                    solve_time_ms=solve_time_ms,
                    solver_name="HiGHS",
                )

        except Exception as e:
            solve_time_ms = (time.perf_counter() - start_time) * 1000.0
            return SolverResult(
                success=False,
                status_code=-99,
                status_message=f"Solver Execution Exception: {str(e)}",
                objective_value=None,
                variable_values={},
                slack_values={},
                solve_time_ms=solve_time_ms,
                solver_name="HiGHS",
            )
