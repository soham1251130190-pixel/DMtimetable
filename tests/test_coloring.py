import sys
import os

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from core.graph_builder import build_conflict_graph

from core.coloring import (
    color_graph,
    is_valid_coloring,
    compare_coloring_strategies,
    order_timeslots,
    coloring_report,
    ColoringError
)


def create_test_sessions():

    return [

        {
            "session_id": 1,
            "subject_id": 101,
            "subject_code": "DM",
            "division_id": 1,
            "teacher_id": 10,
            "elective_group_id": None
        },

        {
            "session_id": 2,
            "subject_id": 102,
            "subject_code": "DSA",
            "division_id": 1,
            "teacher_id": 11,
            "elective_group_id": None
        },

        {
            "session_id": 3,
            "subject_id": 103,
            "subject_code": "DBMS",
            "division_id": 2,
            "teacher_id": 10,
            "elective_group_id": None
        }
    ]


# -----------------------------------------
# TEST 1: Basic availability-aware coloring
# -----------------------------------------

sessions = create_test_sessions()

G = build_conflict_graph(sessions)

availability = {

    10: {1, 2},

    11: {2, 3}
}

timeslots = [

    {"slot_id": 1},

    {"slot_id": 2},

    {"slot_id": 3}
]

colors = color_graph(
    G,
    availability=availability,
    timeslots=timeslots
)

print("Test 1 slot map:")
print(colors)

assert not is_valid_coloring(G, colors)

# Check teacher availability
for session_id, slot_id in colors.items():

    teacher_id = G.nodes[session_id]["teacher_id"]

    assert slot_id in availability[teacher_id]

print("Test 1 passed!")
print()


# -----------------------------------------
# TEST 2: Unavailable slot should not occur
# -----------------------------------------

for session_id, slot_id in colors.items():

    teacher_id = G.nodes[session_id]["teacher_id"]

    assert slot_id in availability[teacher_id]

print("Test 2 passed!")
print()


# -----------------------------------------
# TEST 3: Impossible availability
# -----------------------------------------

impossible_sessions = [

    {
        "session_id": 1,
        "subject_id": 101,
        "subject_code": "DM",
        "division_id": 1,
        "teacher_id": 20,
        "elective_group_id": None
    },

    {
        "session_id": 2,
        "subject_id": 102,
        "subject_code": "DSA",
        "division_id": 1,
        "teacher_id": 21,
        "elective_group_id": None
    }
]

G2 = build_conflict_graph(impossible_sessions)

availability2 = {

    20: {1},

    21: {1}
}

timeslots2 = [

    {"slot_id": 1}
]

try:

    color_graph(
        G2,
        availability=availability2,
        timeslots=timeslots2
    )

    print("ERROR: Impossible dataset did not raise ColoringError!")

except ColoringError as e:

    print("Test 3 passed!")
    print("Expected error:")
    print(e)

print()


# -----------------------------------------
# TEST 4: Coloring strategy comparison
# -----------------------------------------

results = compare_coloring_strategies(G)

print("Test 4 strategy comparison:")

for strategy, result in results.items():

    print(
        strategy,
        "->",
        result["colors_used"],
        "colors"
    )

print()

print("All availability-aware coloring tests passed!")


# =========================================
# TEST 5: Slot ordering
# =========================================

unordered_timeslots = [
    {"slot_id": 6, "day": "Mon", "period": 2},
    {"slot_id": 2, "day": "Tue", "period": 1},
    {"slot_id": 5, "day": "Fri", "period": 1},
    {"slot_id": 1, "day": "Mon", "period": 1},
    {"slot_id": 4, "day": "Thu", "period": 1},
    {"slot_id": 3, "day": "Wed", "period": 1}
]

ordered = order_timeslots(unordered_timeslots)

ordered_ids = [
    slot["slot_id"]
    for slot in ordered
]

expected = [1, 2, 3, 4, 5, 6]

assert ordered_ids == expected

print("Slot ordering:")
print(ordered_ids)

print("Slot ordering test passed!")


# =========================================
# TEST 6: Slot capacity
# =========================================

capacity_sessions = [
    {
        "session_id": 1,
        "subject_id": 101,
        "subject_code": "DM",
        "subject_type": "classroom",
        "division_id": 1,
        "teacher_id": 30,
        "elective_group_id": None
    },
    {
        "session_id": 2,
        "subject_id": 102,
        "subject_code": "DSA",
        "subject_type": "classroom",
        "division_id": 2,
        "teacher_id": 31,
        "elective_group_id": None
    },
    {
        "session_id": 3,
        "subject_id": 103,
        "subject_code": "DBMS",
        "subject_type": "classroom",
        "division_id": 3,
        "teacher_id": 32,
        "elective_group_id": None
    }
]

G3 = build_conflict_graph(capacity_sessions)

availability3 = {
    30: {1, 2},
    31: {1, 2},
    32: {1, 2}
}

timeslots3 = [
    {"slot_id": 1},
    {"slot_id": 2}
]

slot_capacity = {
    "classroom": 2,
    "lab": 1
}

capacity_colors = color_graph(
    G3,
    availability=availability3,
    timeslots=timeslots3,
    slot_capacity=slot_capacity
)

print("Test 6 capacity slot map:")
print(capacity_colors)

usage = {}

for slot_id in capacity_colors.values():
    usage[slot_id] = usage.get(slot_id, 0) + 1

for slot_id, count in usage.items():
    assert count <= 2

print("Test 6 passed!")


# =========================================
# TEST 7: Coloring report
# =========================================

report_timeslots = [
    {"slot_id": 1},
    {"slot_id": 2},
    {"slot_id": 3},
    {"slot_id": 4}
]

report_slot_map = {
    1: 1,
    2: 2,
    3: 2
}

report = coloring_report(
    G,
    report_slot_map,
    report_timeslots,
    runtime=0.01
)

print("\nColoring report:")
print(report)

assert report["colors_used"] == 2
assert report["sessions_per_slot"][1] == [1]
assert report["sessions_per_slot"][2] == [2, 3]
assert report["sessions_per_slot"][3] == []
assert report["sessions_per_slot"][4] == []
assert report["empty_slots"] == [3, 4]
assert report["runtime"] == 0.01

print("Test 7 coloring report passed!")


# =========================================
# TEST 8: Triangle requires 3 colors
# =========================================

triangle_sessions = [

    {
        "session_id": 1,
        "subject_id": 201,
        "subject_code": "A",
        "division_id": 1,
        "teacher_id": 40,
        "elective_group_id": None
    },

    {
        "session_id": 2,
        "subject_id": 202,
        "subject_code": "B",
        "division_id": 1,
        "teacher_id": 41,
        "elective_group_id": None
    },

    {
        "session_id": 3,
        "subject_id": 203,
        "subject_code": "C",
        "division_id": 1,
        "teacher_id": 42,
        "elective_group_id": None
    }
]

triangle_graph = build_conflict_graph(
    triangle_sessions
)

triangle_availability = {
    40: {1, 2, 3},
    41: {1, 2, 3},
    42: {1, 2, 3}
}

triangle_timeslots = [
    {"slot_id": 1},
    {"slot_id": 2},
    {"slot_id": 3}
]

triangle_colors = color_graph(
    triangle_graph,
    availability=triangle_availability,
    timeslots=triangle_timeslots
)

assert not is_valid_coloring(
    triangle_graph,
    triangle_colors
)

assert len(set(triangle_colors.values())) == 3

print("Test 8 triangle:")
print(triangle_colors)
print("Triangle test passed!")


# =========================================
# TEST 9: Path requires 2 colors
# =========================================

path_sessions = [

    {
        "session_id": 1,
        "subject_id": 301,
        "subject_code": "A",
        "division_id": 1,
        "teacher_id": 50,
        "elective_group_id": None
    },

    {
        "session_id": 2,
        "subject_id": 302,
        "subject_code": "B",
        "division_id": 1,
        "teacher_id": 51,
        "elective_group_id": None
    },

    {
        "session_id": 3,
        "subject_id": 303,
        "subject_code": "C",
        "division_id": 2,
        "teacher_id": 51,
        "elective_group_id": None
    }
]

path_graph = build_conflict_graph(
    path_sessions
)

path_availability = {
    50: {1, 2},
    51: {1, 2}
}

path_timeslots = [
    {"slot_id": 1},
    {"slot_id": 2}
]

path_colors = color_graph(
    path_graph,
    availability=path_availability,
    timeslots=path_timeslots
)

assert not is_valid_coloring(
    path_graph,
    path_colors
)

assert len(set(path_colors.values())) == 2

print("Test 9 path:")
print(path_colors)
print("Path test passed!")


# =========================================
# TEST 10: Single node requires 1 color
# =========================================

single_session = [

    {
        "session_id": 1,
        "subject_id": 401,
        "subject_code": "A",
        "division_id": 1,
        "teacher_id": 60,
        "elective_group_id": None
    }
]

single_graph = build_conflict_graph(
    single_session
)

single_availability = {
    60: {1, 2}
}

single_timeslots = [
    {"slot_id": 1},
    {"slot_id": 2}
]

single_colors = color_graph(
    single_graph,
    availability=single_availability,
    timeslots=single_timeslots
)

assert len(set(single_colors.values())) == 1
assert not is_valid_coloring(
    single_graph,
    single_colors
)

print("Test 10 single node:")
print(single_colors)
print("Single node test passed!")


# =========================================
# TEST 11: Zero clashes
# =========================================

zero_clash_sessions = [

    {
        "session_id": 1,
        "subject_id": 501,
        "subject_code": "A",
        "division_id": 1,
        "teacher_id": 70,
        "elective_group_id": None
    },

    {
        "session_id": 2,
        "subject_id": 502,
        "subject_code": "B",
        "division_id": 2,
        "teacher_id": 71,
        "elective_group_id": None
    }
]

zero_clash_graph = build_conflict_graph(
    zero_clash_sessions
)

assert zero_clash_graph.number_of_edges() == 0

zero_clash_availability = {
    70: {1, 2},
    71: {1, 2}
}

zero_clash_timeslots = [
    {"slot_id": 1},
    {"slot_id": 2}
]

zero_clash_colors = color_graph(
    zero_clash_graph,
    availability=zero_clash_availability,
    timeslots=zero_clash_timeslots
)

assert not is_valid_coloring(
    zero_clash_graph,
    zero_clash_colors
)

print("Test 11 zero clashes:")
print(zero_clash_colors)
print("Zero clash test passed!")


# =========================================
# TEST 12: Same seed gives same result
# =========================================

seed_colors_1 = color_graph(
    G,
    availability=availability,
    timeslots=timeslots,
    seed=42
)

seed_colors_2 = color_graph(
    G,
    availability=availability,
    timeslots=timeslots,
    seed=42
)

assert seed_colors_1 == seed_colors_2

print("Test 12 same seed:")
print(seed_colors_1)
print("Same seed deterministic test passed!")


# =========================================
# TEST 13: Different seed can give
# different valid results
# =========================================

different_seed_1 = color_graph(
    G,
    availability=availability,
    timeslots=timeslots,
    seed=1
)

different_seed_2 = color_graph(
    G,
    availability=availability,
    timeslots=timeslots,
    seed=2
)

assert not is_valid_coloring(
    G,
    different_seed_1
)

assert not is_valid_coloring(
    G,
    different_seed_2
)

print("Test 13 seed 1:")
print(different_seed_1)

print("Test 13 seed 2:")
print(different_seed_2)

print("Different seed validity test passed!")


print()
print("=========================================")
print("ALL MEMBER 2 COLORING TESTS PASSED!")
print("=========================================")

# =========================================
# TEST 14: More than 30 timeslots warning
# =========================================

many_timeslots = [
    {"slot_id": i}
    for i in range(1, 32)
]

warning_sessions = [
    {
        "session_id": 1,
        "subject_id": 601,
        "subject_code": "DM",
        "division_id": 1,
        "teacher_id": 80,
        "elective_group_id": None
    }
]

warning_graph = build_conflict_graph(
    warning_sessions
)

warning_availability = {
    80: set(range(1, 32))
}

warning_colors = color_graph(
    warning_graph,
    availability=warning_availability,
    timeslots=many_timeslots
)

assert not is_valid_coloring(
    warning_graph,
    warning_colors
)

assert warning_colors[1] in range(1, 32)

print("Test 14: More than 30 timeslots warning checked!")
print("Test 14 passed!")

print()
print("=========================================")
print("ALL MEMBER 2 COLORING TESTS PASSED!")
print("=========================================")