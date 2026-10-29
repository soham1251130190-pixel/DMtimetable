# 🎓 Smart College Timetable Generator

> **An automated, conflict-free university course scheduling platform powered by Graph Theory, Constraint Satisfaction Programming (CSP), Independent Rule Auditing, and an Interactive React Flow Web Dashboard.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![React Flow](https://img.shields.io/badge/React_Flow-12.0%2B-FF0072?logo=react&logoColor=white)](https://reactflow.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-75%20Passed-success?logo=pytest&logoColor=white)](https://pytest.org/)
[![Deployment](https://img.shields.io/badge/Deployed-Render_%7C_Vercel-46E3B7)](https://vercel.com/)

---

## 📌 Table of Contents
- [Project Overview](#-project-overview)
- [The Two-Stage Divide-and-Conquer Architecture](#-the-two-stage-divide-and-conquer-architecture)
- [Discrete Mathematics (DM) Foundations](#-discrete-mathematics-dm-foundations)
- [System Architecture & Data Flow](#-system-architecture--data-flow)
- [Web Dashboard Features (Member 4)](#-web-dashboard-features-member-4)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Benchmark Datasets](#-benchmark-datasets)
- [Getting Started & Local Setup](#-getting-started--local-setup)
- [API Reference](#-api-reference)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Team & Module Responsibilities](#-team--module-responsibilities)

---

## 📖 Project Overview

Creating an academic timetable for an entire engineering college is a classic scheduling challenge that faculty and department coordinators face at the start of every semester. In a standard college teaching week, dozens of theoretical courses, practical laboratories, subject teachers, and physical classrooms must be scheduled across **5 working days with 6 class periods each day**, providing exactly **30 discrete timeslots**.

In computer science and mathematics, university timetabling is classified as an **NP-complete combinatorial optimization problem** (*Even, Itai & Shamir, 1976*). When solved manually with spreadsheets or paper:
1. **Resource Collisions:** Faculty get accidentally double-booked across classrooms, or student cohorts are scheduled for overlapping subjects.
2. **Physical Constraints:** Classrooms must strictly satisfy student enrollments, practical sessions require dedicated computer laboratories with specialized workstations, and visiting professors are available only during specific hours.
3. **Ergonomic Quality:** Feasible schedules often force students to endure 3-hour idle gap periods between classes or overburden faculty with four back-to-back lectures without rest.

**Smart College Timetable Generator** solves this challenge by mathematically modeling conflicts as an undirected graph, solving timeslots and room assignments through a two-stage pipeline, auditing solutions with an independent constraint verifier, and displaying the results on a modern, dark-glassmorphic React web dashboard.

---

## ⚡ The Two-Stage Divide-and-Conquer Architecture

Rather than assigning timeslots and physical classrooms simultaneously—which causes an exponential explosion in candidate combinations—the system decouples the problem into two distinct, manageable stages:

```
+-------------------------------------------------------------------------------+
| Stage 1: When does each class happen? (Temporal Allocation)                   |
| -> Model sessions as an undirected Conflict Graph in NetworkX                 |
| -> Assign 1 of 30 weekly timeslots using DSATUR Graph Vertex Coloring         |
| -> Guarantee 0 teacher double-bookings and 0 student division overlaps       |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
| Stage 2: Where does each class sit? (Spatial Allocation)                      |
| -> Classrooms only compete with other classes scheduled in the same timeslot  |
| -> Decompose into 30 independent Constraint Satisfaction Problems (CSP)      |
| -> Solve using Minimum Remaining Values (MRV) and Forward Checking (FC)       |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
| Stage 3: How good is the schedule? (Audit & Ergonomic Optimization)           |
| -> Independent Verifier audits 100% of hard constraints with zero solver bias  |
| -> Local-Search Slot-Swap Hill Climber minimizes student idle gaps & fatigue  |
| -> Commit verified timetable atomically to SQLite and expose via REST API    |
+-------------------------------------------------------------------------------+
```

---

## 📐 Discrete Mathematics (DM) Foundations

The scheduling pipeline is a direct, practical application of six core Discrete Mathematics principles:

### 1. Graph Theory: Conflict Graph Modeling
* **Concept:** Academic sessions are represented as vertices $V$. An undirected conflict edge $E$ is established between two sessions if and only if they cannot occur at the same time:
  $$\text{Conflict Graph} = (V, E)$$
* **Conflict Triggers:**
  * **Shared Teacher:** $\text{Teacher}(u) = \text{Teacher}(v)$ (a professor cannot teach in two rooms at once).
  * **Shared Division:** $\text{Division}(u) = \text{Division}(v)$ (students cannot attend two lectures simultaneously).
  * **Shared Elective Basket:** $\text{ElectiveGroup}(u) = \text{ElectiveGroup}(v)$ (parallel electives must avoid overlap to preserve student choice).

### 2. Graph Vertex Coloring: Timeslots as Colors
* **Concept:** Vertex coloring assigns a color to every node such that no two connected nodes share the same color. In our system, colors represent the **30 weekly timeslots** ($5 \text{ days} \times 6 \text{ periods/day}$):
  $$\text{Color}(u) \neq \text{Color}(v) \quad \forall (u, v) \in E$$
* **Feasibility Condition:** A completely clash-free schedule exists if and only if the Chromatic Number $\chi(G)$ satisfies:
  $$\chi(G) \le 30$$

### 3. Cliques & Mathematical Lower Bounds
* **Concept:** A clique is a subset of vertices where every vertex is connected to every other vertex in that subset (all mutually clashing sessions).
* **Lower Bound Theorem:**
  $$\chi(G) \ge \omega(G)$$
  *(where $\omega(G)$ is the size of the maximum complete subgraph / clique).*
* **Instant Infeasibility Detection:** If any group of mutually clashing sessions exceeds 30 (or a faculty member has 16 sessions with only 12 free hours), the system mathematically detects infeasibility in under 5 ms and warns the user immediately without wasting search time.

### 4. Set Theory & Relations
* **Teacher Availability:** For each faculty member $T$, availability is modeled as a subset of free slots $S_T \subseteq \{1, 2, \dots, 30\}$. The engine strictly enforces:
  $$\text{Slot}(s) \in S_{\text{Teacher}(s)}$$
* **Dynamic Room Domain Filtering:**
  $$D_{\text{room}}(s) = \{ r \in R \mid \text{Capacity}(r) \ge \text{Strength}(s) \land \text{Type}(r) = \text{Type}(s) \}$$

### 5. Combinatorics & The Pigeonhole Principle
* **Lab Capacity Bounding:** If $k$ practical laboratory sessions are assigned to timeslot $t$, and the department has only $m$ physical computer laboratories, the Pigeonhole Principle dictates that if $k > m$, at least two lab sessions must collide for the same room.
* **Guarantee:** The Stage 1 coloring engine restricts concurrent practical sessions such that:
  $$\text{ConcurrentLabs}(t) \le \text{TotalPhysicalLabs}$$

### 6. Propositional Logic: The 4 Hard Rules (IF-THEN)
* Evaluated across all scheduled records by an isolated verification script:
  * **Rule 1 (Teacher Exclusivity):** $(\text{Slot}(s_1) = \text{Slot}(s_2)) \implies (\text{Teacher}(s_1) \neq \text{Teacher}(s_2))$
  * **Rule 2 (Cohort Exclusivity):** $(\text{Slot}(s_1) = \text{Slot}(s_2)) \implies (\text{Division}(s_1) \neq \text{Division}(s_2))$
  * **Rule 3 (Room Exclusivity):** $(\text{Slot}(s_1) = \text{Slot}(s_2)) \implies (\text{Room}(s_1) \neq \text{Room}(s_2))$
  * **Rule 4 (Room Type Conformity):** $\text{IsLab}(s) \implies (\text{RoomType}(\text{Room}(s)) = \text{'lab'})$

### 7. Soft Ergonomic Optimization Formula
Once a 100% clash-free schedule is generated, an ergonomic penalty function evaluates schedule quality:
$$\text{Penalty} = (3 \times G) + (2 \times C) + (1 \times S)$$
* **$G$ (Idle Gaps - Weight 3):** Student free periods stranded between lectures on the same day.
* **$C$ (Consecutive Overload - Weight 2):** More than 3 back-to-back lectures without a break.
* **$S$ (Daily Spread - Weight 1):** Uneven lecture distribution across weekdays.
* A slot-swap hill climber performs up to 500 pairwise timeslot exchanges to drive this penalty toward zero.

---

## 🛠️ System Architecture & Data Flow

```
[ SQLite Database (10 Normalized Tables) ]
                   │
                   ▼  (Data Ingestion - Member 1)
[ Session List, Teachers, Rooms, Availability Sets ]
                   │
                   ▼  (Conflict Graph Construction - Member 2)
[ NetworkX Conflict Graph G=(V,E) ] ──► [ Clique Lower Bound ω(G) Check ]
                   │
                   ▼  (Timeslot Coloring - Member 2 & 3)
[ DSATUR Algorithm: Dynamic Saturation Degree Coloring ]
                   │
                   ▼  (Room Allocation - Member 3)
[ 30 Independent Room CSPs: Backtracking + MRV + Forward Checking ]
                   │
                   ▼  (Independent Rule Audit - Member 3)
[ Hard-Constraint Verifier (verifier.py) ] ──[ Pass 100% ]──┐
                   │                                         │
                   ▼  (Ergonomic Optimization - Member 3)   │
[ Slot-Swap Local Search Hill Climber (optimizer.py) ]       │
                   │                                         │
                   ▼                                         │
[ SQLite Atomic Commit: 'timetable' & 'timetable_runs' ] ◄───┘
                   │
                   ▼  (FastAPI REST Endpoints - Member 4)
[ GET /api/timetable/latest | POST /api/generate | GET /api/graph ]
                   │
                   ▼  (Client Delivery - Member 4)
[ React 18 Single-Page Dashboard + @xyflow/react Graph Canvas on Vercel ]
```

---

## 💻 Web Dashboard Features (Member 4)

The web client provides a modern, responsive user experience:

* 🗓️ **5-Day Weekly Academic Grid View:** Matrix view (Monday–Friday, Periods 1–6) displaying Theory vs. Practical Lab badges, room numbers, teacher names, and interactive division filters.
* 📋 **Tabular Timetable List View:** Comprehensive sequential list with instant search, division badge filtering, and clear start/end period timings.
* 🕸️ **Interactive Conflict Graph Canvas (`@xyflow/react`):** Visualizes academic sessions as graph nodes arranged by division columns with highlighted clash lines (edges) indicating shared teachers or cohorts. Users can pan, zoom, drag nodes, and inspect conflict metadata.
* ⚡ **Live Timetable Generation Controls:** Dropdown to select dataset scope, trigger live regeneration with animated spinners, and display real-time generation metrics (runtime in milliseconds, seed number, total sessions placed).
* 🛡️ **Institutional Policy Audit Panel:** Real-time compliance report showing green validation badges confirming 0 teacher clashes, 0 division overlaps, 100% room capacity fit, and the ergonomic quality score.
* ⚠️ **Clean Infeasibility Handling:** When testing over-constrained inputs (e.g., `impossible.db`), the UI displays an intuitive HTTP 422 warning dialog explaining the exact bottleneck rather than crashing.

---

## 🧰 Tech Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Core** | Python | 3.10+ | Core scheduling engine, coloring, CSP, verifier, and optimizer |
| **Graph Modeling** | NetworkX | 3.2+ | Session conflict graph, degree calculation, maximal clique analysis |
| **Database** | SQLite3 | 3.x | 10 normalized relational tables with foreign keys and ACID transactions |
| **REST API** | FastAPI & Uvicorn | 0.100+ | Asynchronous RESTful API exposing generation, schedules, and graph data |
| **Frontend Framework** | React | 18.x | Reactive single-page academic schedule dashboard |
| **Build Tool** | Vite | 5.0+ | Fast modern bundling, HMR, and production optimization |
| **Graph Visualizer** | React Flow (`@xyflow/react`) | 12.0+ | Interactive node-edge conflict graph canvas |
| **Icons & Styling** | Lucide React & Vanilla CSS | Latest | Modern dark glassmorphism theme, accessible colors, and badge cards |
| **Testing Suite** | pytest | 8.0+ | 75 automated unit, boundary, determinism, and integration tests |
| **Cloud Hosting** | Render & Vercel | Production | Render (Python FastAPI server) and Vercel (React Frontend) |

---

## 📂 Project Structure

```text
DMtimetable/
├── backend/                        # FastAPI application entry points
│   ├── api/
│   │   ├── main.py                 # REST API endpoints & CORS configuration
│   │   └── __init__.py
│   ├── core/                       # Core engine re-exports
│   └── test_support/               # Shared testing fixtures
├── core/                           # Stage 1 Graph Engine (Member 2)
│   ├── graph_builder.py            # Conflict graph construction & clique lower bounds
│   ├── coloring.py                 # Availability-aware DSATUR vertex coloring
│   └── __init__.py
├── timetable/                      # Stage 2 & 3 Solver & Database (Member 1 & 3)
│   ├── backend/
│   │   ├── core/
│   │   │   ├── rooms.py            # Backtracking CSP solver with MRV & Forward Checking
│   │   │   ├── verifier.py         # Independent 100% hard-constraint rule auditor
│   │   │   ├── optimizer.py        # Local search slot-swap hill climber
│   │   │   ├── scoring.py          # Soft penalty scoring (gaps, consecutive, spread)
│   │   │   └── pipeline.py         # 8-stage unified timetable execution coordinator
│   │   └── db/                     # SQLite schema definitions & relational queries
│   ├── data_dictionary.md          # Comprehensive database schema documentation
│   └── seed.py                     # Database seeding utilities
├── frontend/                       # React 18 Single-Page Dashboard (Member 4)
│   ├── src/
│   │   ├── components/
│   │   │   ├── TimetableGrid.jsx   # 5-Day x 6-Period schedule matrix view
│   │   │   ├── TimetableList.jsx   # Tabular listing view with filters
│   │   │   ├── ConflictGraph.jsx   # Interactive @xyflow/react conflict network
│   │   │   ├── GenerationSummary.jsx # Quality metrics & verification checklist
│   │   │   └── Header.jsx          # Dataset selector & generation controls
│   │   ├── App.jsx                 # Master application view state & tabs
│   │   ├── main.jsx                # React root mount
│   │   └── index.css               # Glassmorphic dark styling & badges
│   ├── package.json
│   └── vite.config.js
├── tests/                          # Automated Pytest Suite (75 Tests)
│   ├── test_api.py                 # FastAPI endpoint integration tests
│   ├── test_coloring.py            # DSATUR coloring correctness tests
│   ├── test_graph.py               # Conflict edge & clique lower bound tests
│   ├── test_rooms.py               # Room capacity & type CSP matching tests
│   ├── test_verifier.py            # Constraint audit & violation detection tests
│   ├── test_optimizer.py           # Slot-swap penalty reduction tests
│   ├── test_scoring.py             # Soft constraint scoring formula tests
│   ├── test_pipeline.py            # End-to-end pipeline execution tests
│   └── test_integration.py         # Cross-module boundary & determinism tests
├── pyproject.toml                  # Python package configuration
├── requirements.txt                # Python backend dependencies
└── README.md                       # Project documentation
```

---

## 📊 Benchmark Datasets

The engine is benchmarked against four standardized datasets:

| Dataset | Divisions | Teachers | Rooms | Sessions | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`small.db`** | 2 (SE-A, SE-B) | 5 | 4 (3 Class, 1 Lab) | 16 | **Solved:** 16 sessions placed in 16 slots with 0 violations. Fast, hand-checkable benchmark. |
| **`medium.db`** | 4 (SE-A/B, TE-A/B) | 10 | 8 (6 Class, 2 Lab) | 72 | **Solved:** 72 sessions placed in 30 slots with 0 violations. Standard production college instance. |
| **`stress.db`** | 12 (FE, SE, TE, BE) | 30 | 15 (11 Class, 4 Lab) | 261 | **Solved:** 261 sessions placed in 30 slots with 0 violations. Multi-department scalability stress test. |
| **`impossible.db`** | 2 (SE-A, SE-B) | 5 | 4 (3 Class, 1 Lab) | 28 | **Clean Rejection:** Dr. Anita assigned 16 sessions with only 12 free slots. Fails cleanly via Pigeonhole Principle with HTTP 422 alert. |

---

## 🚀 Getting Started & Local Setup

### Prerequisites
* **Python:** 3.10 or higher
* **Node.js:** 18.0 or higher
* **npm:** 9.0 or higher

### 1. Clone the Repository
```bash
git clone https://github.com/swaraliisalunkhe/timetable_generator.git
cd timetable_generator
```

### 2. Backend Setup
```bash
# Create and activate a virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```
The backend API and interactive OpenAPI documentation will be live at:
* API: `http://127.0.0.1:8000`
* Swagger UI Docs: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend

# Install frontend dependencies
npm install

# Start the Vite development server
npm run dev
```
Open your browser and navigate to `http://localhost:5173`.

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Healthcheck endpoint confirming API status. |
| `GET` | `/api/timetable/latest` | Returns the currently active, verified timetable records grouped by division. |
| `GET` | `/api/graph` | Returns nodes (sessions) and conflict edges for React Flow visualization. |
| `POST` | `/api/generate` | Triggers live timetable generation for a specified database with optional seed. |
| `GET` | `/api/datasets` | Lists available benchmark SQLite databases (`small.db`, `medium.db`, etc.). |

---

## 🧪 Testing & Quality Assurance

The repository includes a comprehensive automated test suite consisting of **75 unit, boundary, determinism, and integration tests** executed with `pytest`:

```bash
# Run the complete test suite
pytest -v

# Run with coverage report
pytest --cov=core --cov=timetable/backend/core
```

### Key Guarantees Tested:
1. **Interface Boundaries:** Seamless data handoff between Database $\to$ Conflict Graph $\to$ Solvers $\to$ REST API.
2. **Determinism:** Identical random seed values produce bit-for-bit identical, reproducible timetables.
3. **Database Mutation Safety:** All unit tests run inside isolated temporary databases (`tmp_path`), guaranteeing zero production database corruption.
4. **Clean Failure Handling:** Impossible datasets raise HTTP 422 with clear conflict explanations and never commit incomplete records.

---

## 👥 Team & Module Responsibilities

| Member | Primary Focus & Deliverables | Core Technologies |
| :--- | :--- | :--- |
| **Member 1** | **Data Ingestion & Database Architecture:** Designed the normalized 10-table relational SQLite schema, foreign key integrity rules, query abstractions, and seed dataset generation scripts. | Python, SQLite3, SQL |
| **Member 2** | **Graph Modeling & Theoretical Bounds:** Formulated the session clash graph in NetworkX, degree metrics, conflict adjacency analysis, and maximal clique lower bound $\omega(G)$ calculation. | Python, NetworkX |
| **Member 3** | **Solvers, Independent Verifier & Optimization:** Implemented the availability-aware DSATUR vertex coloring, backtracking CSP room solver with MRV and Forward Checking, isolated hard-constraint rule auditor (`verifier.py`), and slot-swap local search optimizer. | Python, Algorithmic Heuristics |
| **Member 4** | **REST API, Web Dashboard & Cloud Deployment:** Built the asynchronous FastAPI backend endpoints, interactive React 18 single-page dashboard with 5-day grid and list views, `@xyflow/react` conflict visualizer, and deployed the full-stack system on Render and Vercel. | FastAPI, React 18, Vite, React Flow, Render, Vercel |

---

## 📄 License
This course project is developed for the **Discrete Mathematics** curriculum at **Vishwakarma Institute of Technology, Pune**. Released under the [MIT License](LICENSE).
