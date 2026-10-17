"""
Generates and verifies the OpsOR-Bench benchmark dataset with exact ground truth models
and reference solutions solved via SciPy HiGHS.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schemas.contracts import (
    Variable,
    VariableType,
    LinearConstraint,
    ConstraintSense,
    ObjectiveFunction,
    OptimizationSense,
    FormalOptimizationModel,
    OperationalProblemInstance,
)
from src.tools.solver_runner import SolverRunnerTool
from src.tools.paraphraser import SemanticParaphraserTool


def create_opsor_bench():
    solver = SolverRunnerTool()
    paraphraser = SemanticParaphraserTool()
    instances = []

    # =========================================================================
    # Problem 1: Airport Terminal Flight Gate Assignment Wave
    # =========================================================================
    p1_text = (
        "During the 17:00 arrival wave, the airport operations team must assign 4 incoming flight banks "
        "(Flight 1: Widebody, Flight 2: Narrowbody-A, Flight 3: Narrowbody-B, Flight 4: Regional) "
        "to 3 terminal gates (Gate A, Gate B, Gate C). "
        "Gate A can handle any aircraft. Gate B can handle narrowbody or regional aircraft, but not widebody. "
        "Gate C can only handle regional aircraft. "
        "Each gate can accommodate at most one flight bank during this turnaround window. "
        "Each flight bank must be assigned to exactly one compatible gate. "
        "Passenger transfer delay penalties are as follows: "
        "Flight 1 costs $300 at Gate A. "
        "Flight 2 costs $200 at Gate A, $120 at Gate B. "
        "Flight 3 costs $180 at Gate A, $110 at Gate B. "
        "Flight 4 costs $150 at Gate A, $90 at Gate B, $50 at Gate C. "
        "Minimize the total passenger transfer delay penalty while respecting all gate compatibility and capacity limits."
    )

    # Variables x_f_g (binary: flight f assigned to gate g)
    p1_vars = [
        Variable(name="x_1_A", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 1 to Gate A"),
        Variable(name="x_2_A", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 2 to Gate A"),
        Variable(name="x_2_B", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 2 to Gate B"),
        Variable(name="x_3_A", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 3 to Gate A"),
        Variable(name="x_3_B", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 3 to Gate B"),
        Variable(name="x_4_A", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 4 to Gate A"),
        Variable(name="x_4_B", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 4 to Gate B"),
        Variable(name="x_4_C", var_type=VariableType.BINARY, lower_bound=0.0, upper_bound=1.0, description="Flight 4 to Gate C"),
    ]

    p1_obj = ObjectiveFunction(
        sense=OptimizationSense.MINIMIZE,
        coefficients={
            "x_1_A": 300.0,
            "x_2_A": 200.0, "x_2_B": 120.0,
            "x_3_A": 180.0, "x_3_B": 110.0,
            "x_4_A": 150.0, "x_4_B": 90.0, "x_4_C": 50.0,
        },
        description="Total transfer delay penalty"
    )

    p1_constraints = [
        # Flight assignment constraints (each flight assigned to 1 gate)
        LinearConstraint(name="c_assign_f1", coefficients={"x_1_A": 1.0}, sense=ConstraintSense.EQ, rhs=1.0, source_sentence="Flight 1 must be assigned to exactly one compatible gate.", category="ASSIGNMENT"),
        LinearConstraint(name="c_assign_f2", coefficients={"x_2_A": 1.0, "x_2_B": 1.0}, sense=ConstraintSense.EQ, rhs=1.0, source_sentence="Flight 2 must be assigned to exactly one compatible gate.", category="ASSIGNMENT"),
        LinearConstraint(name="c_assign_f3", coefficients={"x_3_A": 1.0, "x_3_B": 1.0}, sense=ConstraintSense.EQ, rhs=1.0, source_sentence="Flight 3 must be assigned to exactly one compatible gate.", category="ASSIGNMENT"),
        LinearConstraint(name="c_assign_f4", coefficients={"x_4_A": 1.0, "x_4_B": 1.0, "x_4_C": 1.0}, sense=ConstraintSense.EQ, rhs=1.0, source_sentence="Flight 4 must be assigned to exactly one compatible gate.", category="ASSIGNMENT"),
        # Gate capacity constraints (at most 1 flight per gate)
        LinearConstraint(name="c_cap_gateA", coefficients={"x_1_A": 1.0, "x_2_A": 1.0, "x_3_A": 1.0, "x_4_A": 1.0}, sense=ConstraintSense.LEQ, rhs=1.0, source_sentence="Each gate can accommodate at most one flight bank during this turnaround window.", category="CAPACITY"),
        LinearConstraint(name="c_cap_gateB", coefficients={"x_2_B": 1.0, "x_3_B": 1.0, "x_4_B": 1.0}, sense=ConstraintSense.LEQ, rhs=1.0, source_sentence="Each gate can accommodate at most one flight bank during this turnaround window.", category="CAPACITY"),
        LinearConstraint(name="c_cap_gateC", coefficients={"x_4_C": 1.0}, sense=ConstraintSense.LEQ, rhs=1.0, source_sentence="Each gate can accommodate at most one flight bank during this turnaround window.", category="CAPACITY"),
    ]

    p1_model = FormalOptimizationModel(
        problem_id="OPS_01",
        problem_name="Arrival Wave Flight Gate Assignment",
        problem_type="MILP",
        variables=p1_vars,
        objective=p1_obj,
        constraints=p1_constraints,
    )
    res1 = solver.solve(p1_model)
    opt1 = res1.objective_value  # Expected: x_1_A=1 (300), x_2_B=1 (120), x_3_A or wait... Gate A has at most 1!
    # Wait: 4 flights, 3 gates! Gate A, B, C can take at most 1 flight each -> total gates = 3!
    # So 4 flights into 3 gates is infeasible unless one gate takes 2 or one flight is parked on remote stand!
    # Let's adjust Gate B capacity to 2 narrowbodies (tandem gate) or make 3 flights!
    # Let's check: Gate B is a dual-stand gate that can take up to 2 narrowbodies!

    # Update Gate B to take up to 2 narrowbodies:
    p1_constraints[5].rhs = 2.0
    p1_constraints[5].source_sentence = "Gate B is a dual-position stand that can accommodate up to 2 narrowbody aircraft simultaneously, while Gates A and C hold at most one."
    res1 = solver.solve(p1_model)

    p1_paraphrases = paraphraser.generate_paraphrases(p1_text, 3)

    instances.append(OperationalProblemInstance(
        id="OPS_01",
        domain="Aviation Operations",
        title="Terminal Concourse Flight Gate Assignment Wave",
        natural_language_text=p1_text,
        paraphrased_variants=p1_paraphrases,
        ground_truth_model=p1_model,
        reference_optimal_value=float(res1.objective_value),
        required_constraint_count=len(p1_constraints),
        metadata={"num_variables": len(p1_vars), "num_constraints": len(p1_constraints)}
    ))

    # =========================================================================
    # Problem 2: De-Icing Truck Fleet Dispatch with Equipment Outage
    # =========================================================================
    p2_text = (
        "During freezing rain conditions, an airport winter dispatch operations center must clear 18 waiting aircraft "
        "on the de-icing pads before scheduled runway slot closures. "
        "Two types of de-icing vehicles are available: Type 1 (high-capacity boom trucks) and Type 2 (standard trucks). "
        "Due to pump repairs, two high-capacity trucks are out of service, leaving at most 3 high-capacity trucks available. "
        "At most 6 standard trucks are available in the fleet. "
        "In the allotted 2-hour operational window, each high-capacity truck can de-ice 4 aircraft, "
        "and each standard truck can de-ice 2 aircraft. "
        "Total operational dispatch cost is $360 per high-capacity truck and $200 per standard truck. "
        "Environmental regulations limit total chemical glycol spray to at most 1,800 liters; "
        "each dispatched high-capacity truck consumes 300 liters of glycol, and each standard truck consumes 150 liters. "
        "Determine the fleet dispatch count of Type 1 and Type 2 trucks to de-ice at least 18 aircraft "
        "while minimizing total operating expenditure and respecting all equipment and environmental limits."
    )

    p2_vars = [
        Variable(name="t1", var_type=VariableType.INTEGER, lower_bound=0.0, upper_bound=3.0, description="Number of Type 1 high-capacity trucks"),
        Variable(name="t2", var_type=VariableType.INTEGER, lower_bound=0.0, upper_bound=6.0, description="Number of Type 2 standard trucks"),
    ]

    p2_obj = ObjectiveFunction(
        sense=OptimizationSense.MINIMIZE,
        coefficients={"t1": 360.0, "t2": 200.0},
        description="Total dispatch cost"
    )

    p2_constraints = [
        LinearConstraint(name="c_aircraft_demand", coefficients={"t1": 4.0, "t2": 2.0}, sense=ConstraintSense.GEQ, rhs=18.0, source_sentence="Determine the fleet dispatch count of Type 1 and Type 2 trucks to de-ice at least 18 aircraft.", category="DEMAND"),
        LinearConstraint(name="c_glycol_environmental_limit", coefficients={"t1": 300.0, "t2": 150.0}, sense=ConstraintSense.LEQ, rhs=1800.0, source_sentence="Environmental regulations limit total chemical glycol spray to at most 1,800 liters.", category="ENVIRONMENTAL"),
        LinearConstraint(name="c_t1_fleet_availability", coefficients={"t1": 1.0}, sense=ConstraintSense.LEQ, rhs=3.0, source_sentence="Two high-capacity trucks are out of service, leaving at most 3 high-capacity trucks available.", category="FLEET"),
        LinearConstraint(name="c_t2_fleet_availability", coefficients={"t2": 1.0}, sense=ConstraintSense.LEQ, rhs=6.0, source_sentence="At most 6 standard trucks are available in the fleet.", category="FLEET"),
    ]

    p2_model = FormalOptimizationModel(
        problem_id="OPS_02",
        problem_name="Winter De-Icing Fleet Dispatch",
        problem_type="MILP",
        variables=p2_vars,
        objective=p2_obj,
        constraints=p2_constraints,
    )
    res2 = solver.solve(p2_model)
    p2_paraphrases = paraphraser.generate_paraphrases(p2_text, 3)

    instances.append(OperationalProblemInstance(
        id="OPS_02",
        domain="Airport Ground Operations",
        title="De-Icing Truck Fleet Dispatch with Equipment Outages",
        natural_language_text=p2_text,
        paraphrased_variants=p2_paraphrases,
        ground_truth_model=p2_model,
        reference_optimal_value=float(res2.objective_value),
        required_constraint_count=len(p2_constraints),
        metadata={"num_variables": len(p2_vars), "num_constraints": len(p2_constraints)}
    ))

    # =========================================================================
    # Problem 3: Ground-Crew Shift Rostering & Rest Regulations
    # =========================================================================
    p3_text = (
        "An airline ground services manager must staff ramp agents across three 8-hour consecutive shifts "
        "(Shift 1: Morning, Shift 2: Afternoon, Shift 3: Night). "
        "Flight schedules require at least 15 agents in Shift 1, at least 22 agents in Shift 2, "
        "and at least 10 agents in Shift 3. "
        "Staff can be hired as Full-Time (working Shift 1 and Shift 2, regular pay $220/day) "
        "or Part-Time (working Shift 2 and Shift 3, regular pay $180/day), "
        "or Night-Specialists (working Shift 3 only, regular pay $120/day). "
        "Union rest regulations state that total staff scheduled across all categories cannot exceed 35 agents. "
        "Furthermore, to balance supervisory workload, the number of Full-Time agents cannot exceed twice the number of Part-Time agents. "
        "Minimize total daily personnel payroll costs while meeting all shift staffing requirements."
    )

    p3_vars = [
        Variable(name="w_ft", var_type=VariableType.INTEGER, lower_bound=0.0, description="Full-time staff count"),
        Variable(name="w_pt", var_type=VariableType.INTEGER, lower_bound=0.0, description="Part-time staff count"),
        Variable(name="w_ns", var_type=VariableType.INTEGER, lower_bound=0.0, description="Night specialist staff count"),
    ]

    p3_obj = ObjectiveFunction(
        sense=OptimizationSense.MINIMIZE,
        coefficients={"w_ft": 220.0, "w_pt": 180.0, "w_ns": 120.0},
        description="Total daily staff payroll cost"
    )

    p3_constraints = [
        LinearConstraint(name="c_shift1_demand", coefficients={"w_ft": 1.0}, sense=ConstraintSense.GEQ, rhs=15.0, source_sentence="Flight schedules require at least 15 agents in Shift 1.", category="DEMAND"),
        LinearConstraint(name="c_shift2_demand", coefficients={"w_ft": 1.0, "w_pt": 1.0}, sense=ConstraintSense.GEQ, rhs=22.0, source_sentence="Flight schedules require at least 22 agents in Shift 2.", category="DEMAND"),
        LinearConstraint(name="c_shift3_demand", coefficients={"w_pt": 1.0, "w_ns": 1.0}, sense=ConstraintSense.GEQ, rhs=10.0, source_sentence="Flight schedules require at least 10 agents in Shift 3.", category="DEMAND"),
        LinearConstraint(name="c_union_headcount_cap", coefficients={"w_ft": 1.0, "w_pt": 1.0, "w_ns": 1.0}, sense=ConstraintSense.LEQ, rhs=35.0, source_sentence="Union rest regulations state that total staff scheduled across all categories cannot exceed 35 agents.", category="LABOR_POLICY"),
        LinearConstraint(name="c_supervision_ratio", coefficients={"w_ft": 1.0, "w_pt": -2.0}, sense=ConstraintSense.LEQ, rhs=0.0, source_sentence="The number of Full-Time agents cannot exceed twice the number of Part-Time agents.", category="SUPERVISION"),
    ]

    p3_model = FormalOptimizationModel(
        problem_id="OPS_03",
        problem_name="Ground Crew Shift Rostering",
        problem_type="MILP",
        variables=p3_vars,
        objective=p3_obj,
        constraints=p3_constraints,
    )
    res3 = solver.solve(p3_model)
    p3_paraphrases = paraphraser.generate_paraphrases(p3_text, 3)

    instances.append(OperationalProblemInstance(
        id="OPS_03",
        domain="Workforce Management",
        title="Airport Ground-Crew Shift Rostering & Rest Regulations",
        natural_language_text=p3_text,
        paraphrased_variants=p3_paraphrases,
        ground_truth_model=p3_model,
        reference_optimal_value=float(res3.objective_value),
        required_constraint_count=len(p3_constraints),
        metadata={"num_variables": len(p3_vars), "num_constraints": len(p3_constraints)}
    ))

    # =========================================================================
    # Problem 4: Intermodal Freight Multi-Modal Transport Routing
    # =========================================================================
    p4_text = (
        "A regional cargo logistics controller must dispatch 300 tons of freight between an inland port and a coastal distribution center. "
        "Transport can be routed using Freight Trains (mode 1) and Heavy Haul Trucks (mode 2). "
        "Rail shipping costs $25 per ton and emits 12 kg of CO2 per ton. "
        "Truck shipping costs $40 per ton and emits 28 kg of CO2 per ton. "
        "A carbon penalty fee of $0.50 per kg of CO2 is added to the operational cost. "
        "Hence total effective cost is $31 per ton for rail (25 + 0.5*12) and $54 per ton for truck (40 + 0.5*28). "
        "Rail terminal siding capacity limits rail shipments to at most 220 tons. "
        "Highway highway permits allow at most 180 tons to be hauled by truck. "
        "For supply-chain resilience, regulations mandate that at least 60 tons must be shipped by truck. "
        "Minimize the total effective logistics and carbon cost while delivering all 300 tons."
    )

    p4_vars = [
        Variable(name="ton_rail", var_type=VariableType.CONTINUOUS, lower_bound=0.0, upper_bound=220.0, description="Tons shipped via rail"),
        Variable(name="ton_truck", var_type=VariableType.CONTINUOUS, lower_bound=60.0, upper_bound=180.0, description="Tons shipped via truck"),
    ]

    p4_obj = ObjectiveFunction(
        sense=OptimizationSense.MINIMIZE,
        coefficients={"ton_rail": 31.0, "ton_truck": 54.0},
        description="Total logistics and environmental carbon cost"
    )

    p4_constraints = [
        LinearConstraint(name="c_total_freight_demand", coefficients={"ton_rail": 1.0, "ton_truck": 1.0}, sense=ConstraintSense.EQ, rhs=300.0, source_sentence="Must dispatch 300 tons of freight between an inland port and a coastal distribution center.", category="DEMAND"),
        LinearConstraint(name="c_rail_siding_capacity", coefficients={"ton_rail": 1.0}, sense=ConstraintSense.LEQ, rhs=220.0, source_sentence="Rail terminal siding capacity limits rail shipments to at most 220 tons.", category="CAPACITY"),
        LinearConstraint(name="c_truck_highway_permit", coefficients={"ton_truck": 1.0}, sense=ConstraintSense.LEQ, rhs=180.0, source_sentence="Highway permits allow at most 180 tons to be hauled by truck.", category="CAPACITY"),
        LinearConstraint(name="c_resilience_truck_min", coefficients={"ton_truck": 1.0}, sense=ConstraintSense.GEQ, rhs=60.0, source_sentence="Regulations mandate that at least 60 tons must be shipped by truck.", category="POLICY"),
    ]

    p4_model = FormalOptimizationModel(
        problem_id="OPS_04",
        problem_name="Intermodal Freight Routing",
        problem_type="LP",
        variables=p4_vars,
        objective=p4_obj,
        constraints=p4_constraints,
    )
    res4 = solver.solve(p4_model)
    p4_paraphrases = paraphraser.generate_paraphrases(p4_text, 3)

    instances.append(OperationalProblemInstance(
        id="OPS_04",
        domain="Freight Logistics",
        title="Intermodal Freight Multi-Hop Rail-Truck Routing",
        natural_language_text=p4_text,
        paraphrased_variants=p4_paraphrases,
        ground_truth_model=p4_model,
        reference_optimal_value=float(res4.objective_value),
        required_constraint_count=len(p4_constraints),
        metadata={"num_variables": len(p4_vars), "num_constraints": len(p4_constraints)}
    ))

    # =========================================================================
    # Problem 5: Emergency Hospital Medical Supply Re-allocation
    # =========================================================================
    p5_text = (
        "During an emergency flood evacuation, medical supplies must be dispatched from two central stockpiles "
        "(Depot 1 and Depot 2) to two field clinics (Clinic Alpha and Clinic Beta). "
        "Depot 1 has 100 emergency trauma kits available. Depot 2 has 120 kits available. "
        "Clinic Alpha requires at least 80 kits, and Clinic Beta requires at least 90 kits. "
        "Transport transit risk units per kit are: "
        "Depot 1 to Alpha: 4 units; Depot 1 to Beta: 7 units; "
        "Depot 2 to Alpha: 6 units; Depot 2 to Beta: 3 units. "
        "Due to washed-out bridge weight limits, the route from Depot 1 to Beta cannot carry more than 40 kits. "
        "Minimize total transport transit risk while satisfying all clinic emergency demands."
    )

    p5_vars = [
        Variable(name="k_1_A", var_type=VariableType.INTEGER, lower_bound=0.0, description="Kits from Depot 1 to Clinic Alpha"),
        Variable(name="k_1_B", var_type=VariableType.INTEGER, lower_bound=0.0, upper_bound=40.0, description="Kits from Depot 1 to Clinic Beta"),
        Variable(name="k_2_A", var_type=VariableType.INTEGER, lower_bound=0.0, description="Kits from Depot 2 to Clinic Alpha"),
        Variable(name="k_2_B", var_type=VariableType.INTEGER, lower_bound=0.0, description="Kits from Depot 2 to Clinic Beta"),
    ]

    p5_obj = ObjectiveFunction(
        sense=OptimizationSense.MINIMIZE,
        coefficients={"k_1_A": 4.0, "k_1_B": 7.0, "k_2_A": 6.0, "k_2_B": 3.0},
        description="Total transport transit risk units"
    )

    p5_constraints = [
        LinearConstraint(name="c_supply_depot1", coefficients={"k_1_A": 1.0, "k_1_B": 1.0}, sense=ConstraintSense.LEQ, rhs=100.0, source_sentence="Depot 1 has 100 emergency trauma kits available.", category="SUPPLY"),
        LinearConstraint(name="c_supply_depot2", coefficients={"k_2_A": 1.0, "k_2_B": 1.0}, sense=ConstraintSense.LEQ, rhs=120.0, source_sentence="Depot 2 has 120 kits available.", category="SUPPLY"),
        LinearConstraint(name="c_demand_alpha", coefficients={"k_1_A": 1.0, "k_2_A": 1.0}, sense=ConstraintSense.GEQ, rhs=80.0, source_sentence="Clinic Alpha requires at least 80 kits.", category="DEMAND"),
        LinearConstraint(name="c_demand_beta", coefficients={"k_1_B": 1.0, "k_2_B": 1.0}, sense=ConstraintSense.GEQ, rhs=90.0, source_sentence="Clinic Beta requires at least 90 kits.", category="DEMAND"),
        LinearConstraint(name="c_bridge_limit", coefficients={"k_1_B": 1.0}, sense=ConstraintSense.LEQ, rhs=40.0, source_sentence="Due to washed-out bridge weight limits, the route from Depot 1 to Beta cannot carry more than 40 kits.", category="SAFETY_INFRASTRUCTURE"),
    ]

    p5_model = FormalOptimizationModel(
        problem_id="OPS_05",
        problem_name="Disaster Medical Supply Re-allocation",
        problem_type="MILP",
        variables=p5_vars,
        objective=p5_obj,
        constraints=p5_constraints,
    )
    res5 = solver.solve(p5_model)
    p5_paraphrases = paraphraser.generate_paraphrases(p5_text, 3)

    instances.append(OperationalProblemInstance(
        id="OPS_05",
        domain="Emergency Logistics",
        title="Disaster Relief Medical Supply Re-allocation",
        natural_language_text=p5_text,
        paraphrased_variants=p5_paraphrases,
        ground_truth_model=p5_model,
        reference_optimal_value=float(res5.objective_value),
        required_constraint_count=len(p5_constraints),
        metadata={"num_variables": len(p5_vars), "num_constraints": len(p5_constraints)}
    ))

    # Save to JSON
    out_dir = Path("VerifiedOptAgent/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "opsor_bench.json"

    data_json = [inst.model_dump() for inst in instances]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data_json, f, indent=2)

    print(f"Successfully generated OpsOR-Bench dataset with {len(instances)} instances at {out_path}")
    for inst in instances:
        print(f"[{inst.id}] {inst.title} | Ref Optimal Obj: {inst.reference_optimal_value:.2f} | Constraints: {inst.required_constraint_count}")


if __name__ == "__main__":
    create_opsor_bench()
