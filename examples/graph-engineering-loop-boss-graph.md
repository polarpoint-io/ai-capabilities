# GRAPH.md — Declaring Agent Topology as a Reviewable Artifact

This file shows the same request handled three ways — loop, supervisor ("boss"), and
graph — so you can see exactly what changes when topology moves from implicit to
declared. Place a file like the graph section in your repo root (`GRAPH.md` or
alongside your `AGENTS.md`) so a multi-agent system's shape is something a human
reviews in a PR, not something they reconstruct from logs.

Companion to: *From Harness to Graph: The Fourth Era of Working With AI*

---

## Shape 1 — Loop

One agent, one job, ReAct-style. There's nothing to declare because there's nothing to
coordinate — this is the right shape until you're actually running more than one agent
on related work.

```yaml
shape: loop
agent: fix-bug
harness: harnesses/fix-bug.md   # still needs its own constraints, see the harness post
```

---

## Shape 2 — Supervisor ("boss")

A dispatcher classifies the incoming request and routes it to a specialist. The
topology is a fan-out from one node — implicit in the dispatcher's routing logic
unless you write it down.

```yaml
shape: supervisor
dispatcher: intake
routes:
  - when: classification == "bug"
    to: fix-bug
  - when: classification == "migration"
    to: write-migration
  - when: classification == "docs"
    to: update-docs
```

**Review note:** because the routing rules live inside the dispatcher's prompt or
code, adding a new route is a behavior change that's easy to miss in review. Writing
it as data (like the block above) instead of leaving it embedded in a prompt is the
first step toward graph engineering, even before you adopt a graph runtime.

---

## Shape 3 — Graph

Nodes, edges, and the state that crosses them are declared up front. This is the
worked example from the blog post: an intake agent classifies the request, a
harnessed fix-bug agent implements it, a deterministic test runner verifies it, and
either a human reviews the result or the loop retries.

```yaml
shape: graph
nodes:
  - id: intake
    type: agent
    role: classify-request
    harness: harnesses/intake.md
  - id: fix-bug
    type: agent
    role: implement-fix
    harness: harnesses/fix-bug.md
  - id: run-tests
    type: deterministic
    role: verify
  - id: human-review
    type: human

edges:
  - from: intake
    to: fix-bug
    when: classification == "bug"
  - from: fix-bug
    to: run-tests
  - from: run-tests
    to: human-review
    when: tests == "pass"
  - from: run-tests
    to: fix-bug
    when: tests == "fail"   # the retry edge

state:
  schema:
    request_id: string
    classification: string
    diff: string
    test_result: string
```

---

## Topology change review levels

Use these when you're the one reviewing a PR that touches `GRAPH.md`, the same way
you'd apply approval tiers to an AGENTS.md change.

| Change | Review level | Why |
|---|---|---|
| Add a new edge between existing nodes | Standard PR review | Doesn't change what any node is allowed to do, just who it can hand off to |
| Add a new node | Standard PR review, harness required | A new node needs its own harness before it joins the graph — no bare nodes |
| Change the state schema | Careful review | Every node reading or writing that state needs to agree on the new shape |
| Remove a human-review node | Requires a second approver | You're removing the one non-agent checkpoint in the path |
| Add a cycle / retry edge | Careful review, must have a bound | An unbounded retry edge is a loop with extra steps and an infinite budget — cap it |

---

## The tell that you don't actually have a graph

If you can't produce a file like this — nodes, edges, conditions, all of it — for
your multi-agent system, you don't have graph engineering yet. You have a loop with
extra steps and a routing function nobody's written down. Writing the file is the
exercise, independent of which runtime executes it.

---

*Companion artifact for [From Harness to Graph: The Fourth Era of Working With AI](https://polarpoint.io/blog/from-harness-to-graph-2026). See also `examples/karpathy-claude-md.md` for the harness-layer counterpart — every node above still needs one.*
