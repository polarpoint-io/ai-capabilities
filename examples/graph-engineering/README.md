# Graph Engineering: Loop, Boss, Graph

Companion examples for [From Harness to Graph: The Fourth Era of Working With AI](https://polarpoint.io/blog/from-harness-to-graph-2026).

Three runnable, dependency-free Python scripts showing the same request — "fix the
null pointer in checkout" — handled by each of the three shapes described in the
post. No LLM calls, no framework — the point is the *shape* of the coordination,
not the implementation.

| File | Shape | What to notice |
|---|---|---|
| `loop_example.py` | Loop | One agent, one job. No coordination logic exists because there's nothing to coordinate. |
| `boss_example.py` | Supervisor ("boss") | The `ROUTES` dict is the routing table — it works, but it's implicit inside the function. Nothing forces it to stay documented. |
| `graph_example.py` | Graph | `NODES` and `EDGES` are the same idea as `ROUTES`, promoted to an explicit, printable, reviewable structure — including a capped retry edge. |
| `graph-engineering-loop-boss-graph.md` | All three, as declared artifacts | The `GRAPH.md`-style file you'd actually put in a repo, plus a topology change review table for whoever reviews the PR. |

## Run them

```bash
python3 loop_example.py
python3 boss_example.py
python3 graph_example.py
```

`graph_example.py` runs the fix-bug -> run-tests cycle twice on purpose (the first
patch is incomplete, tests fail, the retry edge sends it back to fix-bug, the second
patch passes) so you can see the retry edge and its cap (`MAX_RETRIES = 2`) actually
do something, not just sit in a comment.

## The point of the progression

`boss_example.py`'s `ROUTES` dict and `graph_example.py`'s `NODES`/`EDGES` are doing
the same job — deciding who handles what next. The difference is that the graph
version is a structure you can iterate over, print, and diff. That's the whole claim
in the blog post: graph engineering isn't a new capability, it's taking a decision
that already existed in your code and making it inspectable.

None of these examples include a harness — see
[karpathy-claude-md.md](../karpathy-claude-md.md) and the
[harness-engineering post](https://polarpoint.io/blog/harness-engineering-evolution-2026)
for that layer. Every node in a real graph still needs one.
