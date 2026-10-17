# VerifiedOptAgent: Multi-Agent Auto-Formalization of Natural Language Operations into Verified Optimization Models

**Course:** AI4015 – Agentic Artificial Intelligence (Fall 2026)  
**Deliverable:** Semester Project – Phase 1 (Technical Foundation & Baseline)  
**Project Track:** G1 – LLM Agents that Translate Natural Language into Verified Optimization Models  
**Supervisor:** Muhammad Sajjad  
**Group Code:** G1-01  
**Group Members:**  
- **Muhammad Awais** (22I-0930) — *Group Head / Architecture & Multi-Agent Verification*  

---

## 1. Project Overview

Operations teams in mission-critical environments (such as aviation ground handling, freight logistics, and disaster relief) describe planning problems in colloquial natural language (e.g., *"Can we handle the 17:00 arrival wave if two de-icing trucks are out of service?"*). However, industrial decision support systems demand formal mathematical optimization models (Linear Programming / Mixed-Integer Linear Programming).

Recent state-of-the-art auto-formalization systems (such as *LLMOPT*, ICLR 2025, and *OptiMUS*, ICML 2024) translate text into solver code, but rely exclusively on compiler return codes and solver execution syntax. They lack **requirement-level semantic verification**—silently dropping domain constraints, misassigning coefficient directions, and failing to know when to refuse an uncertain or contradictory specification. In operational settings, a silently dropped constraint can ground an entire aircraft fleet.

**VerifiedOptAgent** introduces the missing semantic verification and calibrated decision layer through a 5-role multi-agent architecture:
1. **Parser Agent:** Decomposes unstructured natural language into decision variables, bounds, and categorized requirements with source sentence provenance.
2. **Formalizer Agent:** Auto-formalizes parsed specifications into structured mathematical optimization contracts and executable solver representations.
3. **Solver-Runner Tool:** Sandboxed execution engine running HiGHS via SciPy, extracting primal status, optimal objective values, allocations, and constraint slack variables.
4. **Verifier Agent:** Conducts requirement-level constraint coverage (CCR), hallucinated constraint auditing (HCR), and linguistic paraphrase invariance (SIS) testing.
5. **Explainer & Conformal Decision Agent:** Implements split-conformal risk control to mathematically guarantee an empirical error rate $\le \alpha$ (e.g., $\alpha = 0.05$), selectively outputting `ACCEPT_AND_EXECUTE`, `ESCALATE_TO_HUMAN`, or `ABSTAIN_UNCERTAIN` alongside actionable audit explanations.

---

## 2. System Architecture

```
                                  [ Operational Problem Text ]
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │   ParserAgent   │
                                      └────────┬────────┘
                                               │ (Variables, Bounds, Sentences)
                                               ▼
                                      ┌─────────────────┐
                                      │ FormalizerAgent │
                                      └────────┬────────┘
                                               │ (Pydantic Formal Optimization Model)
                                               ▼
                                      ┌─────────────────┐
                                      │SolverRunnerTool │ (SciPy HiGHS Solver Backend)
                                      └────────┬────────┘
                                               │ (Primal Status, Objective, Slacks)
                                               ▼
                     ┌──────────────────────────────────────────────────┐
                     │                  VerifierAgent                   │
                     │  - Constraint Coverage Rate (CCR)                │
                     │  - Hallucinated Constraint Audit (HCR)           │
                     │  - Semantic Paraphrase Invariance (SIS)          │
                     │  - Slack Degeneracy & Feasibility Check          │
                     └─────────────────────────┬────────────────────────┘
                                               │ (VerificationReport)
                                               ▼
                     ┌──────────────────────────────────────────────────┐
                     │            Explainer & Conformal Agent           │
                     │  - Non-Conformity Scoring: s(x, y)               │
                     │  - Conformal Quantile Risk Threshold: q          │
                     └─────────────────────────┬────────────────────────┘
                                               │
                  ┌────────────────────────────┼────────────────────────────┐
                  ▼                            ▼                            ▼
       [ ACCEPT_AND_EXECUTE ]         [ ESCALATE_TO_HUMAN ]        [ ABSTAIN_UNCERTAIN ]
       (Guaranteed Risk <= alpha)    (Flagged Ambiguity Review)     (Refuse High-Risk)
```

---

## 3. Repository Structure

```
VerifiedOptAgent/
├── data/
│   ├── opsor_bench.json            # 5 realistic operational planning problem instances
│   ├── perturbation_suite.json     # 20 controlled perturbation & corruption test cases
│   ├── generate_dataset.py         # OpsOR-Bench dataset generator
│   └── generate_perturbations.py   # Perturbation suite generator
├── src/
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── contracts.py            # Pydantic contracts for models, constraints, reports
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base agent and unified LLM provider
│   │   ├── parser.py               # Requirement Decomposer & Entity Extractor
│   │   ├── formalizer.py           # Mathematical Model Formalizer
│   │   ├── verifier.py             # Requirement-Level Semantic Verifier (Gap 1)
│   │   ├── conformal.py            # Conformal Risk Control & Refusal Engine (Gap 2)
│   │   └── explainer.py            # Operational Dispatch Explainer & Triage
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── solver_runner.py        # HiGHS MILP/LP sandboxed execution engine
│   │   └── paraphraser.py          # Semantic linguistic perturbation generator
│   └── pipeline/
│       ├── __init__.py
│       ├── baseline_single.py      # Non-Agentic Single-LLM baseline
│       ├── baseline_llmopt.py      # Base-Paper LLMOPT Iterative Solver Debugger
│       └── verified_multi.py       # Proposed 5-Agent Verified Pipeline
├── evaluation/
│   ├── __init__.py
│   ├── evaluate.py                 # 3-Way Comparative Benchmark Runner
│   ├── metrics.py                  # Evaluation metrics (Accuracy, CCR, HCR, SIS, Risk)
│   └── benchmark_results.json      # Structured benchmark evaluation results
├── tests/
│   └── test_pipeline.py            # Unit and integration test suite
├── run_baseline.py                 # End-to-end interactive CLI runner
├── requirements.txt                # Python package dependencies
├── .gitignore                      # Git exclusion rules
└── README.md                       # Project documentation
```

---

## 4. Benchmark Dataset: OpsOR-Bench

OpsOR-Bench comprises realistic multi-step planning scenarios grounded in operational constraints:
1. **OPS_01 (Airport Operations):** *Terminal Concourse Flight Gate Assignment Wave* — Binary integer programming allocating incoming flight banks across gate compatibility classes. Reference Objective: `$580.00`.
2. **OPS_02 (Ground Logistics):** *De-Icing Truck Fleet Dispatch with Equipment Outages* — Mixed-integer programming scheduling high-capacity and standard de-icing trucks under equipment outages and glycol runoff limits. Reference Objective: `$1680.00`.
3. **OPS_03 (Workforce Management):** *Airport Ground-Crew Shift Rostering & Rest Regulations* — Integer programming scheduling personnel across consecutive shifts under mandatory union rest rules. Reference Objective: `$4980.00`.
4. **OPS_04 (Intermodal Freight):** *Intermodal Freight Multi-Hop Rail-Truck Routing* — Linear programming balancing rail track fees, truck hauling costs, and carbon tax levies. Reference Objective: `$11140.00`.
5. **OPS_05 (Emergency Logistics):** *Disaster Relief Medical Supply Re-allocation* — Transportation network flow routing trauma packages from depots to clinics under bridge infrastructure limits. Reference Objective: `$590.00`.

---

## 5. Initial Quantitative Baseline Results

The initial baseline evaluation was performed across 20 test cases spanning 4 perturbation classes (Clean, Paraphrase, Dropped Constraints, and Contradictory Constraints) on OpsOR-Bench:

| Evaluation Metric | Single-LLM Baseline | Base Paper: LLMOPT (ICLR 2025) | Proposed Multi-Agent Verified |
| :--- | :---: | :---: | :---: |
| **Formulation Accuracy (%)** | 50.0% | 50.0% | 30.0% (Clean only) |
| **Constraint Coverage Rate (CCR %)** | *N/A (No Verifier)* | *N/A (No Verifier)* | **75.0%** |
| **Hallucinated Constraint Rate (HCR %)** | *Unchecked* | *Unchecked* | **0.0%** |
| **Semantic Invariance Score (SIS %)** | *Unchecked* | *Unchecked* | **68.4%** |
| **Safety / Calibrated Control Rate (%)** | 75.0% | 75.0% | **100.0%** |
| **Accepted Error Rate (Target $\le 5\%$)** | **33.3%** | **33.3%** | **0.0%** (Risk Guarantee Met) |
| **Decisions: Accepted** | 15 | 15 | 6 |
| **Decisions: Escalated to Human** | 0 *(Cannot Escalate)* | 0 *(Cannot Escalate)* | **2** |
| **Decisions: Refused (Abstained)** | 5 | 5 | **12** |
| **Average Tokens per Instance** | 245.9 | 262.4 | 678.4 |
| **Average Solve Latency** | 0.0018s | 0.0022s | 0.0012s |

### Key Experimental Insights:
- **Flaw in Current SOTA (LLMOPT):** LLMOPT blindly accepted models with silently dropped constraints because the remaining sub-model was technically solvable, resulting in a **33.3% accepted error rate**.
- **Conformal Risk Bound:** VerifiedOptAgent achieved **0.0% accepted error rate** ($\le \alpha = 0.05$), successfully escalating ambiguous cases to human dispatchers and refusing contradictory inputs.

---

## 6. Installation & Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.14 on Windows 11)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Awais014/VerifiedOptAgent.git
cd VerifiedOptAgent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Unit Tests
```bash
python tests/test_pipeline.py
```

### 4. Run the End-to-End Baseline & Benchmark
```bash
python run_baseline.py
```

---

## 7. Next Phase Milestones (Phase 2 Preview)

- [ ] Connect online cloud LLMs (Gemini 2.5 Flash / Pro and GPT-4o) via API keys with full dynamic prompt generation.
- [ ] Expand OpsOR-Bench to 50 large-scale multi-period operational scenarios.
- [ ] Implement Weisfeiler-Lehman (WL) graph-isomorphism model equivalence verification.
- [ ] Perform fine-grained token-budget ablation experiments to plot Pareto curves of Accuracy vs Compute.
