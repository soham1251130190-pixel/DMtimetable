# Data Dictionary: Smart College Timetable Generator

SQLite, ten tables. Foreign keys are ON in every connection (`db.connect()`). Slots are numbered day-major: Mon P1 = 1 … Mon P6 = 6, Tue P1 = 7 … Fri P6 = 30.

| Table | Column | Type | Meaning / rule |
|---|---|---|---|
| **teachers** | teacher_id | INTEGER PK | |
| | name | TEXT | |
| | department | TEXT | e.g. Mathematics, Computer Science |
| | max_lectures_per_day | INTEGER ≥ 1 | Hard cap on lectures per day (default 4) |
| **subjects** | subject_id | INTEGER PK | |
| | code | TEXT UNIQUE | e.g. `CS201` |
| | name | TEXT | |
| | type | TEXT | `theory` / `lab` / `elective` (CHECK). Labs need a `lab` room |
| | lectures_per_week | INTEGER ≥ 1 | Number of session rows generated per division |
| | elective_group_id | INTEGER, NULL | Set **iff** type = `elective` (CHECK). Subjects sharing an id form one elective group |
| **divisions** | division_id | INTEGER PK | |
| | name | TEXT UNIQUE | e.g. `TE-A` |
| | year | INTEGER ≥ 1 | Study year |
| | strength | INTEGER > 0 | Students; a room must have capacity ≥ strength |
| **rooms** | room_id | INTEGER PK | |
| | name | TEXT UNIQUE | e.g. `R101`, `LAB-1` |
| | capacity | INTEGER > 0 | |
| | room_type | TEXT | `classroom` / `lab` (CHECK) |
| **timeslots** | slot_id | INTEGER PK | 1 … 30 |
| | day | TEXT | `Mon` … `Fri` |
| | period | INTEGER ≥ 1 | 1-based period of the day |
| | start_time, end_time | TEXT | `HH:MM` |
| | | | UNIQUE(day, period) |
| **teaching_assignments** | division_id, subject_id | FK, composite PK | One teacher per (division, subject) |
| | teacher_id | FK → teachers | Who teaches it. Source for `sessions` |
| **sessions** | session_id | INTEGER PK | One row per weekly lecture = one graph node |
| | subject_id, division_id, teacher_id | FK | Composite FK to `teaching_assignments`, so they always agree |
| | session_no | INTEGER ≥ 1 | 1 … lectures_per_week; UNIQUE(division_id, subject_id, session_no) |
| | elective_group_id | INTEGER, NULL | Copy of the subject's group (checked by `validate_data.py`) |
| **teacher_availability** | teacher_id, slot_id | FK | UNIQUE(teacher_id, slot_id). Seeds write all 30 rows per teacher |
| | is_available | INTEGER | 1 = free, 0 = blocked. A missing row counts as not available |
| **timetable_runs** | run_id | INTEGER PK AUTOINCREMENT | One per generation attempt |
| | created_at | TEXT | Defaults to current timestamp |
| | status | TEXT | `running` / `completed` / `failed` / `sample` (CHECK) |
| | colors_used | INTEGER, NULL | Distinct slots used by Stage 1 |
| | penalty_score | REAL, NULL | Soft-constraint score from the Stage 2 scorer |
| **timetable** | run_id | FK → timetable_runs | ON DELETE CASCADE |
| | session_id | FK → sessions | PK(run_id, session_id): a session is placed once per run |
| | slot_id | FK → timeslots | |
| | room_id | FK → rooms, NULL | NULL allowed so slot-only (Stage 1) results can be saved. UNIQUE(run_id, slot_id, room_id): one session per room per slot |

**Indexes:** `sessions(teacher_id)`, `sessions(division_id)`, `timetable(run_id)`.

## Datasets (`seed.py`)

| Dataset | Divisions | Teachers | Subjects | Rooms | Sessions | Notes |
|---|---|---|---|---|---|---|
| small | 2 | 5 | 5 | 3 classrooms + 1 lab | 16 | Hand-checkable |
| medium | 4 | 10 | 11 | 6 classrooms + 2 labs | 72 | 1 elective group, 3–4 blocked slots per teacher; also the committed `timetable.db` |
| stress | 12 | 30 | 31 | 11 classrooms + 4 labs | 261 | 2 elective groups, random blocked slots |
| impossible | 2 | 5 | 5 | 3 classrooms + 1 lab | 28 | Dr. Anita Deshmukh: 16 sessions, 12 available slots |

Small, medium and stress each include one saved **sample run** (`status = 'sample'`) that satisfies every hard constraint, so they are known to be schedulable.

## Conventions to know

- **Elective groups:** `elective_group_id` marks subjects that students choose between. The sample runs follow the strict reading: sessions of one group never share a slot. Member 2 decides how this becomes `'elective'` graph edges.
- **One session = one period.** Labs are 1-period sessions (2-hour blocks are a stretch goal).
- **Ids are stable.** Seeds use fixed ids and a fixed random seed; to add a teacher or room, append it to the end of the list in `seed.py` and re-seed.

## Rebuild commands

```
python init_db.py --reset                 # empty database, 30 timeslots
python seed.py                            # data/*.db and timetable.db (medium)
python seed.py --dataset small --db timetable.db
python validate_data.py --all             # small, medium, stress pass; impossible fails
python -m pytest ../tests                 # from backend/db
```
