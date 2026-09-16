"""
Shape 1: Loop

One agent, ReAct-style: observe, think, act, repeat until done.
No coordination logic exists because there's nothing to coordinate yet.

Run: python3 loop_example.py
"""


def fix_bug_agent(state: dict) -> dict:
    """Mocked single agent. In reality this is an LLM call plus tool use,
    wrapped in its own harness (see the harness-engineering post)."""
    step = state.get("step", 0)

    if step == 0:
        print("  [agent] observing: request says 'fix the null pointer in checkout'")
        state["diff"] = None
        state["step"] = 1
    elif step == 1:
        print("  [agent] thinking: null check missing before .total access")
        state["step"] = 2
    elif step == 2:
        print("  [agent] acting: writing patch")
        state["diff"] = "checkout.py: add `if cart is not None` guard"
        state["step"] = 3
    elif step == 3:
        print("  [agent] observing: patch looks complete, done")
        state["done"] = True

    return state


def run_loop(request: str) -> dict:
    state = {"request": request, "done": False}
    print(f"Loop agent handling: {request!r}")
    while not state["done"]:
        state = fix_bug_agent(state)
    return state


if __name__ == "__main__":
    final = run_loop("fix the null pointer in checkout")
    print(f"\nResult: {final['diff']}")
