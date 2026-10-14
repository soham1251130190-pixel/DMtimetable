from sys import path
from os import path as os_path

path.append(os_path.dirname(os_path.dirname(os_path.abspath(__file__))))

from core.graph_builder import build_conflict_graph, graph_statistics, graph_to_json


def test_graph_builder():
    sessions = [
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
        },
        {
            "session_id": 4,
            "subject_id": 104,
            "subject_code": "AI",
            "division_id": 3,
            "teacher_id": 12,
            "elective_group_id": 1
        },
        {
            "session_id": 5,
            "subject_id": 105,
            "subject_code": "ML",
            "division_id": 4,
            "teacher_id": 13,
            "elective_group_id": 1
        }
    ]

    G = build_conflict_graph(sessions)

    # Check number of nodes
    assert G.number_of_nodes() == 5

    # Session 1 and 2 have same division
    assert G.has_edge(1, 2)

    # Session 1 and 3 have same teacher
    assert G.has_edge(1, 3)

    # Session 4 and 5 have same elective group
    assert G.has_edge(4, 5)

    # Check conflict reasons
    assert "division" in G[1][2]["reasons"]
    assert "teacher" in G[1][3]["reasons"]
    assert "elective" in G[4][5]["reasons"]

    print("Graph builder test passed!")


if __name__ == "__main__":
    test_graph_builder()

# =========================================
# TEST: Graph statistics
# =========================================

statistics_sessions = [
    {
        "session_id": 1,
        "subject_id": 101,
        "subject_code": "DM",
        "subject_type": "classroom",
        "division_id": 1,
        "teacher_id": 10,
        "elective_group_id": None
    },
    {
        "session_id": 2,
        "subject_id": 102,
        "subject_code": "DSA",
        "subject_type": "classroom",
        "division_id": 1,
        "teacher_id": 11,
        "elective_group_id": None
    },
    {
        "session_id": 3,
        "subject_id": 103,
        "subject_code": "DBMS",
        "subject_type": "classroom",
        "division_id": 2,
        "teacher_id": 11,
        "elective_group_id": None
    },
    {
        "session_id": 4,
        "subject_id": 104,
        "subject_code": "OS",
        "subject_type": "classroom",
        "division_id": 3,
        "teacher_id": 12,
        "elective_group_id": None
    }
]

statistics_graph = build_conflict_graph(
    statistics_sessions
)

stats = graph_statistics(statistics_graph)

print("\nGraph statistics:")
print("Nodes:", stats["nodes"])
print("Edges:", stats["edges"])
print("Density:", stats["density"])
print("Maximum degree:", stats["max_degree"])
print("Connected components:", stats["connected_components"])
print("Color lower bound:", stats["color_lower_bound"])

assert stats["nodes"] == 4
assert stats["edges"] == 2
assert stats["max_degree"] == 2
assert stats["connected_components"] == 2
assert stats["color_lower_bound"] >= 2

print("Graph statistics test passed!")


# =========================================
# TEST: Graph to JSON
# =========================================

slot_map = {
    1: 1,
    2: 2,
    3: 2,
    4: 3
}

graph_json = graph_to_json(
    statistics_graph,
    slot_map
)

print("\nGraph JSON:")
print(graph_json)

assert "nodes" in graph_json
assert "edges" in graph_json

assert len(graph_json["nodes"]) == 4
assert len(graph_json["edges"]) == 2

assert graph_json["nodes"][0]["id"] == 1
assert "subject" in graph_json["nodes"][0]
assert "division" in graph_json["nodes"][0]
assert "teacher" in graph_json["nodes"][0]
assert "slot_id" in graph_json["nodes"][0]

print("Graph to JSON test passed!")