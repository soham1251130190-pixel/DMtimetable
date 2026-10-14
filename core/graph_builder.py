"""
Member 2: Conflict Graph & Slot Coloring

Conflict rules:
1. Same teacher -> conflict
2. Same division -> conflict
3. Same elective group -> conflict

Default elective rule:
Sessions in the same elective group are treated as conflicting,
so they cannot be assigned to the same timeslot.
"""

import networkx as nx


def build_conflict_graph(sessions):
    G = nx.Graph()

    for session in sessions:
        session_id = session["session_id"]

        G.add_node(
            session_id,
            subject_id=session.get("subject_id"),
            subject_code=session.get("subject_code"),
            subject_type=session.get("subject_type"),
            division_id=session.get("division_id"),
            teacher_id=session.get("teacher_id"),
            elective_group_id=session.get("elective_group_id")
        )

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):

            s1 = sessions[i]
            s2 = sessions[j]

            reasons = []

            # Same teacher
            if (
                s1.get("teacher_id") is not None
                and s1.get("teacher_id") == s2.get("teacher_id")
            ):
                reasons.append("teacher")

            # Same division
            if (
                s1.get("division_id") is not None
                and s1.get("division_id") == s2.get("division_id")
            ):
                reasons.append("division")

            # Same elective group
            if (
                s1.get("elective_group_id") is not None
                and s1.get("elective_group_id")
                == s2.get("elective_group_id")
            ):
                reasons.append("elective")

            if reasons:
                G.add_edge(
                    s1["session_id"],
                    s2["session_id"],
                    reasons=reasons
                )

    return G


def graph_statistics(G):
    """
    Calculate basic sanity statistics for the conflict graph.

    Returns:
        Dictionary containing graph statistics.
    """

    number_of_nodes = G.number_of_nodes()
    number_of_edges = G.number_of_edges()

    # Graph density
    if number_of_nodes <= 1:
        density = 0
    else:
        density = nx.density(G)

    # Maximum degree and connected components
    if number_of_nodes == 0:
        max_degree = 0
        connected_components = 0
    else:
        max_degree = max(
            dict(G.degree()).values()
        )

        connected_components = (
            nx.number_connected_components(G)
        )

    # Lower bound for number of colors.
    # A clique of size k requires at least k colors.
    if number_of_nodes == 0:
        color_lower_bound = 0
    else:
        cliques = list(nx.find_cliques(G))

        color_lower_bound = max(
            len(clique)
            for clique in cliques
        )

    # Warn if the graph mathematically requires
    # more colors than the available 30 timeslots.
    if color_lower_bound > 30:
        print(
            f"WARNING: The graph requires at least "
            f"{color_lower_bound} colors, which exceeds "
            "the available 30 timeslots."
        )

    return {
        "nodes": number_of_nodes,
        "edges": number_of_edges,
        "density": density,
        "max_degree": max_degree,
        "connected_components": connected_components,
        "color_lower_bound": color_lower_bound
    }


def graph_to_json(G, slot_map):
    """
    Convert the conflict graph and slot assignments
    into a JSON-friendly dictionary.
    """

    nodes = []

    for node in G.nodes:

        nodes.append({
            "id": node,
            "subject": G.nodes[node].get("subject_code"),
            "division": G.nodes[node].get("division_id"),
            "teacher": G.nodes[node].get("teacher_id"),
            "slot_id": slot_map.get(node)
        })

    edges = []

    for u, v, data in G.edges(data=True):

        edges.append({
            "source": u,
            "target": v,
            "reasons": data.get("reasons", [])
        })

    return {
        "nodes": nodes,
        "edges": edges
    }