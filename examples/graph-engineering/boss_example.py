"""
Shape 2: Supervisor ("boss")

A dispatcher classifies the incoming request and routes it to a specialist.
Notice the routing table lives inside this function - that's the thing graph
engineering pulls out into a declared, reviewable artifact (see GRAPH.md).

Run: python3 boss_example.py
"""


def classify(request: str) -> str:
    """The dispatcher's classification step - in a real system this is an
    LLM call, here it's a stand-in so the example runs with no dependencies."""
    if "bug" in request or "null pointer" in request or "crash" in request:
        return "bug"
    if "migration" in request or "schema" in request:
        return "migration"
    if "docs" in request or "readme" in request:
        return "docs"
    return "unknown"


def fix_bug_specialist(request: str) -> str:
    print("  [fix-bug specialist] patching the reported bug")
    return "checkout.py: add null guard"


def write_migration_specialist(request: str) -> str:
    print("  [migration specialist] writing schema migration")
    return "0042_add_index.sql"


def update_docs_specialist(request: str) -> str:
    print("  [docs specialist] updating README")
    return "README.md: fixed stale command example"


# This dict IS the routing table. It's implicit - nothing forces you to keep
# it in sync with what the classifier actually returns, and there's no
# artifact a reviewer can diff to see "routing changed" versus "logic changed".
ROUTES = {
    "bug": fix_bug_specialist,
    "migration": write_migration_specialist,
    "docs": update_docs_specialist,
}


def run_supervisor(request: str) -> str:
    print(f"Supervisor handling: {request!r}")
    classification = classify(request)
    print(f"  [dispatcher] classified as: {classification}")

    specialist = ROUTES.get(classification)
    if specialist is None:
        return f"no specialist for classification: {classification}"

    return specialist(request)


if __name__ == "__main__":
    for req in [
        "fix the null pointer in checkout",
        "add a migration for the new schema",
        "fix a stale command in the readme",
    ]:
        result = run_supervisor(req)
        print(f"  -> {result}\n")
