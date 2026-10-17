"""
Structured Data Contracts for Verified LLM Optimization Modeling.
Defines Pydantic schemas for problem parsing, formal mathematical modeling,
solver execution results, multi-agent verification checks, and conformal refusal.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class VariableType(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    INTEGER = "INTEGER"
    BINARY = "BINARY"


class OptimizationSense(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class ConstraintSense(str, Enum):
    LEQ = "<="
    GEQ = ">="
    EQ = "=="


class Variable(BaseModel):
    name: str = Field(..., description="Unique variable identifier, e.g., 'x_gate_1'")
    var_type: VariableType = Field(default=VariableType.CONTINUOUS, description="Type of variable")
    lower_bound: float = Field(default=0.0, description="Lower bound")
    upper_bound: Optional[float] = Field(default=None, description="Upper bound if applicable")
    description: str = Field(default="", description="Natural language meaning of this variable")


class LinearConstraint(BaseModel):
    name: str = Field(..., description="Unique constraint identifier, e.g., 'c_capacity_gate_A'")
    coefficients: Dict[str, float] = Field(..., description="Mapping from variable name to linear coefficient")
    sense: ConstraintSense = Field(..., description="Constraint relation ('<=', '>=', '==')")
    rhs: float = Field(..., description="Right-hand side numeric constant")
    source_sentence: str = Field(default="", description="Exact sentence in original prompt that implies this constraint")
    category: str = Field(default="OPERATIONAL", description="Constraint category, e.g., 'RESOURCE', 'SAFETY', 'POLICY'")


class ObjectiveFunction(BaseModel):
    sense: OptimizationSense = Field(..., description="MINIMIZE or MAXIMIZE")
    coefficients: Dict[str, float] = Field(..., description="Mapping from variable name to objective coefficient")
    constant: float = Field(default=0.0, description="Constant offset in objective function")
    description: str = Field(default="", description="Description of target objective")


class FormalOptimizationModel(BaseModel):
    problem_id: str = Field(..., description="Unique problem instance ID")
    problem_name: str = Field(..., description="Descriptive problem title")
    problem_type: str = Field(default="MILP", description="Optimization class: 'LP' or 'MILP'")
    variables: List[Variable] = Field(default_factory=list, description="Set of decision variables")
    objective: ObjectiveFunction = Field(..., description="Mathematical objective function")
    constraints: List[LinearConstraint] = Field(default_factory=list, description="Set of linear constraints")
    latex_formulation: Optional[str] = Field(default=None, description="LaTeX representation of the model")
    executable_python_code: Optional[str] = Field(default=None, description="Executable SciPy HiGHS code string")


class SolverResult(BaseModel):
    success: bool = Field(..., description="Whether solver achieved optimal solution")
    status_code: int = Field(default=0, description="Solver status code")
    status_message: str = Field(..., description="Status message, e.g., 'Optimization terminated successfully'")
    objective_value: Optional[float] = Field(default=None, description="Primal optimal objective value")
    variable_values: Dict[str, float] = Field(default_factory=dict, description="Optimal decision variable values")
    slack_values: Dict[str, float] = Field(default_factory=dict, description="Constraint slack values")
    solve_time_ms: float = Field(default=0.0, description="Time taken by solver in milliseconds")
    solver_name: str = Field(default="HiGHS", description="Solver engine used")


class VerificationCheck(BaseModel):
    check_name: str = Field(..., description="Identifier of verification check")
    passed: bool = Field(..., description="Whether the specific verification test passed")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the verifier")
    details: str = Field(default="", description="Diagnostic details or rationale")
    flagged_issues: List[str] = Field(default_factory=list, description="Specific discrepancies identified")


class VerificationReport(BaseModel):
    overall_passed: bool = Field(..., description="Overall verification verdict")
    constraint_coverage_score: float = Field(..., ge=0.0, le=1.0, description="Fraction of prompt requirements covered")
    hallucinated_constraint_count: int = Field(default=0, description="Count of constraints with no ground truth basis")
    omitted_constraints: List[str] = Field(default_factory=list, description="Requirements in text omitted from model")
    semantic_invariance_score: float = Field(..., ge=0.0, le=1.0, description="Invariance score under rephrasing")
    slack_degeneracy_detected: bool = Field(default=False, description="Whether unconstrained/degenerate slacks detected")
    checks: List[VerificationCheck] = Field(default_factory=list, description="List of granular verification check results")
    verifier_notes: str = Field(default="", description="Qualitative summary of verification outcome")


class DecisionAction(str, Enum):
    ACCEPT_AND_EXECUTE = "ACCEPT_AND_EXECUTE"
    ABSTAIN_UNCERTAIN = "ABSTAIN_UNCERTAIN"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class CalibratedDecision(BaseModel):
    action: DecisionAction = Field(..., description="Calibrated operational decision")
    non_conformity_score: float = Field(..., description="Conformal non-conformity measure s(x, y)")
    conformal_threshold_q: float = Field(..., description="Calibrated quantile threshold at level 1-alpha")
    risk_level_alpha: float = Field(default=0.05, description="Significance level alpha (guaranteed error bound)")
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0, description="Empirical confidence score")
    explanation: str = Field(..., description="Actionable operational explanation for the human supervisor")
    required_review_items: List[str] = Field(default_factory=list, description="Items needing domain expert review")


class OperationalProblemInstance(BaseModel):
    id: str = Field(..., description="Instance identifier")
    domain: str = Field(..., description="Application domain, e.g. 'Aviation', 'Logistics', 'Rostering'")
    title: str = Field(..., description="Problem title")
    natural_language_text: str = Field(..., description="Unstructured natural language specification")
    paraphrased_variants: List[str] = Field(default_factory=list, description="Semantically equivalent rephrased versions")
    ground_truth_model: Optional[FormalOptimizationModel] = Field(default=None, description="Gold-standard verified model")
    reference_optimal_value: Optional[float] = Field(default=None, description="Ground-truth optimal objective value")
    required_constraint_count: int = Field(default=0, description="Number of independent operational requirements")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Instance metadata")
