import networkx as nx
import random


class ColoringError(Exception):
    """Raised when a valid timetable coloring cannot be found."""
    pass


def order_timeslots(timeslots):
    """
    Order timeslots by period first and day second.

    Example:
    Mon P1
    Tue P1
    Wed P1
    Thu P1
    Fri P1
    Mon P2
    Tue P2
    ...
    """

    if not timeslots:
        return []

    day_order = {
        "Mon": 0,
        "Monday": 0,
        "Tue": 1,
        "Tuesday": 1,
        "Wed": 2,
        "Wednesday": 2,
        "Thu": 3,
        "Thursday": 3,
        "Fri": 4,
        "Friday": 4
    }

    # If timeslots are simple slot IDs
    if not isinstance(timeslots[0], dict):
        return sorted(timeslots)

    def sort_key(slot):

        day = slot.get("day")
        period = slot.get("period")

        if period is None:
            period = slot.get("period_no")

        if day in day_order and period is not None:
            return (
                period,
                day_order[day]
            )

        # Fallback if day/period information is missing
        return (
            float("inf"),
            slot.get("slot_id", 0)
        )

    return sorted(timeslots, key=sort_key)


def color_graph(
    G,
    availability=None,
    timeslots=None,
    slot_capacity=None,
    seed=0
):
    """
    Availability-aware DSATUR coloring.

    Returns:
        Dictionary:
        session_id -> slot_id
    """

    if G.number_of_nodes() == 0:
        return {}

    # Random generator controlled by seed.
    # Same seed gives deterministic results.
    rng = random.Random(seed)

    if availability is None:
        availability = {}

    if timeslots is None:
        raise ColoringError("Timeslots are required.")

    # Order slots in timetable-friendly order
    ordered_timeslots = order_timeslots(timeslots)

    slot_ids = []

    for slot in ordered_timeslots:

        if isinstance(slot, dict):
            slot_ids.append(slot["slot_id"])
        else:
            slot_ids.append(slot)

    if not slot_ids:
        raise ColoringError("No timeslots available.")

    if len(slot_ids) > 30:
        print(
            f"WARNING: {len(slot_ids)} timeslots are available. "
            "This is more than the recommended limit of 30."
        )

    # Store final assignment
    coloring = {}

    # Track how many sessions use each slot
    slot_usage = {
        slot_id: 0
        for slot_id in slot_ids
    }

    # Track available slots for every session
    allowed_slots = {}

    for node in G.nodes:

        teacher_id = G.nodes[node].get("teacher_id")

        # If teacher availability exists, use it
        if teacher_id in availability:

            allowed = set(
                availability[teacher_id]
            )

            # Keep only slots that actually exist
            allowed = allowed.intersection(
                slot_ids
            )

        else:

            # If availability is missing,
            # allow all slots.
            allowed = set(slot_ids)

        if not allowed:

            raise ColoringError(
                f"Session {node} has no available "
                f"timeslots for teacher {teacher_id}."
            )

        allowed_slots[node] = allowed

    # -----------------------------
    # DSATUR COLORING
    # -----------------------------

    uncolored = set(G.nodes)

    while uncolored:

        best_node = None
        best_key = None

        for node in uncolored:

            # Slots already used by neighbors
            neighbor_slots = {
                coloring[neighbor]
                for neighbor in G.neighbors(node)
                if neighbor in coloring
            }

            # Slots still possible
            remaining_slots = (
                allowed_slots[node]
                - neighbor_slots
            )

            saturation = len(neighbor_slots)
            degree = G.degree[node]

            # Choose:
            # 1. Fewest remaining slots
            # 2. Highest saturation
            # 3. Highest degree
            key = (
                len(remaining_slots),
                -saturation,
                -degree,
                node
            )

            if best_key is None or key < best_key:

                best_key = key
                best_node = node

        node = best_node

        # Find valid slots for this session
        neighbor_slots = {
            coloring[neighbor]
            for neighbor in G.neighbors(node)
            if neighbor in coloring
        }

        possible_slots = (
            allowed_slots[node]
            - neighbor_slots
        )

        # Apply capacity if provided
        if slot_capacity is not None:

            possible_slots = {
                slot
                for slot in possible_slots
                if slot_usage[slot]
                < _get_capacity(
                    G,
                    node,
                    slot_capacity
                )
            }

        if not possible_slots:

            blocking_neighbors = [
                neighbor
                for neighbor in G.neighbors(node)
                if neighbor in coloring
                and coloring[neighbor]
                in allowed_slots[node]
            ]

            teacher_id = G.nodes[node].get(
                "teacher_id"
            )

            raise ColoringError(
                f"Unable to assign a slot to session {node}. "
                f"Teacher {teacher_id} has no valid "
                f"available slot. "
                f"Blocking neighbors: {blocking_neighbors}"
            )

        # Choose a valid slot.
        # Slots are initially ordered according to
        # the timetable order.
        ordered_possible_slots = sorted(
            possible_slots,
            key=slot_ids.index
        )

        # Use the seed to introduce deterministic
        # variation when multiple valid slots exist.
        if len(ordered_possible_slots) > 1:
            rng.shuffle(ordered_possible_slots)

        chosen_slot = ordered_possible_slots[0]

        coloring[node] = chosen_slot

        slot_usage[chosen_slot] += 1

        uncolored.remove(node)

    # IMPORTANT:
    # Return only after ALL sessions are colored.
    return coloring


def _get_capacity(G, node, slot_capacity):
    """
    Determine capacity for a session.

    If subject_type matches a capacity category,
    use that capacity.

    Otherwise use classroom capacity.
    """

    subject_type = G.nodes[node].get(
        "subject_type"
    )

    if subject_type in slot_capacity:
        return slot_capacity[subject_type]

    if "classroom" in slot_capacity:
        return slot_capacity["classroom"]

    return float("inf")


def is_valid_coloring(G, colors):
    """
    Check whether conflicting sessions have
    been assigned the same slot.

    Returns:
        List of conflicting edges.
        Empty list means coloring is valid.
    """

    conflicts = []

    for u, v in G.edges:

        if u in colors and v in colors:

            if colors[u] == colors[v]:
                conflicts.append((u, v))

    return conflicts


def compare_coloring_strategies(G):
    """
    Compare the three baseline NetworkX
    coloring strategies.
    """

    strategies = [
        "largest_first",
        "smallest_last",
        "saturation_largest_first"
    ]

    results = {}

    for strategy in strategies:

        coloring = nx.coloring.greedy_color(
            G,
            strategy=strategy
        )

        number_of_colors = (
            max(coloring.values()) + 1
            if coloring
            else 0
        )

        results[strategy] = {
            "coloring": coloring,
            "colors_used": number_of_colors
        }

    return results


def coloring_report(G, slot_map, timeslots, runtime=None):
    """
    Generate a report for the final timetable coloring.

    Shows:
    - Number of slots used
    - Sessions assigned to each slot
    - Empty slots
    - Runtime
    """

    all_slot_ids = []

    for slot in timeslots:
        if isinstance(slot, dict):
            all_slot_ids.append(slot["slot_id"])
        else:
            all_slot_ids.append(slot)

    sessions_per_slot = {
        slot_id: []
        for slot_id in all_slot_ids
    }

    for session_id, slot_id in slot_map.items():
        if slot_id in sessions_per_slot:
            sessions_per_slot[slot_id].append(session_id)

    used_slots = [
        slot_id
        for slot_id in all_slot_ids
        if sessions_per_slot[slot_id]
    ]

    empty_slots = [
        slot_id
        for slot_id in all_slot_ids
        if not sessions_per_slot[slot_id]
    ]

    report = {
        "colors_used": len(used_slots),
        "sessions_per_slot": sessions_per_slot,
        "empty_slots": empty_slots,
        "runtime": runtime
    }

    return report

