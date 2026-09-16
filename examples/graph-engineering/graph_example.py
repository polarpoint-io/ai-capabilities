"""
Shape 3: Graph

Topology is declared up front as data (nodes, edges, conditions) instead of
being discovered from a pile of function calls. This is the runnable version
of the GRAPH.md example: intake -> fix-bug -> run-tests -> human-review,
with a capped retry edge back to fix-bug when tests fail.

The point isn't the specific engine below - it's that the graph is a thing
you can print, diff, and review before it runs. Compare this file's shape
to boss_example.py's ROUTES dict: same idea, promoted from "implicit inside
a function" to "explicit and inspectable."

Run: python3 graph_example.py
"""

MAX_RETRIES = 2  # caps the retry edge - see the review table in GRAPH.md


def intake_node(state: dict) -> dict:
    print("  [intake] classifying request")
    state["classification"] = "bug"
    return state


def fix_bug_node(state: dict) -> dict:
    attempt = state.get("retries", 0)
    print(f"  [fix-bug] implementing fix (attempt {attempt + 1})")
    # Simulate: the first attempt ships an incomplete patch, the retry fixes it.
    state["diff"] = "checkout.py: partial guard" if attempt == 0 else "checkout.py: full null guard"
    return state


def run_tests_node(state: dict) -> dict:
    attempt = state.get("retries", 0)
    passed = attempt > 0  # fails on the first pass, passes after the retry
    state["test_result"] = "pass" if passed else "fail"
    print(f"  [run-tests] result: {state['test_result']}")
    return state


def human_review_node(state: dict) -> dict:
    print(f"  [human-review] ready for review: {state['diff']}")
    return state


# The graph, declared as data. This is what you'd generate from GRAPH.md,
# or in a real system, what GRAPH.md is generated FROM - either direction,
# the point is the two stay in sync and both are reviewable.
NODES = {
    "intake": intake_node,
    "fix-bug": fix_bug_node,
    "run-tests": run_tests_node,
    "human-review": human_review_node,
}

EDGES = [
    ("intake", "fix-bug", lambda s: s.get("classification") == "bug"),
    ("fix-bug", "run-tests", lambda s: True),
    ("run-tests", "human-review", lambda s: s.get("test_result") == "pass"),
    ("run-tests", "fix-bug", lambda s: s.get("test_result") == "fail"),  # retry edge
]


def next_node(current: str, state: dict) -> str | None:
    for frm, to, condition in EDGES:
        if frm == current and condition(state):
            return to
    return None


def run_graph(request_id: str) -> dict:
    state = {"request_id": request_id, "retries": 0}
    current = "intake"
    path = [current]

    while current != "human-review":
        state = NODES[current](state)
        target = next_node(current, state)

        if target is None:
            raise RuntimeError(f"no outgoing edge from '{current}' matched state: {state}")

        if target == "fix-bug" and current == "run-tests":
            state["retries"] += 1
            if state["retries"] > MAX_RETRIES:
                raise RuntimeError(f"retry edge exceeded MAX_RETRIES={MAX_RETRIES}, stopping")

        current = target
        path.append(current)

    state = NODES[current](state)
    print(f"\nPath taken: {' -> '.join(path)}")
    return state


if __name__ == "__main__":
    final_state = run_graph(request_id="req-001")
    print(f"Final state: {final_state}")
