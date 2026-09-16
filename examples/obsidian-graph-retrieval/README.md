# Obsidian Graph Retrieval

Companion tool for [Your Obsidian Vault Is Already a Graph. Stop Feeding It to the Model Flat.](https://polarpoint.io/blog/obsidian-graph-engineering-token-efficiency-2026)

`retrieve.py` treats a vault's `[[wikilinks]]` as a declared graph and retrieves
context by BFS traversal from an anchor note instead of embedding similarity
search. No dependencies beyond the standard library.

## Why a hub cutoff matters

Every real vault ends up with at least one Map-of-Content note that links to
everything, "so nothing gets lost." Without protection, one hop through that
note pulls in your whole vault regardless of relevance. `sample_vault/` has
exactly this shape: a 6-note cluster about graph engineering, ten unrelated
personal notes (recipes, fitness logs, travel planning), and a `MOC - All
Posts.md` hub that links to all sixteen other notes.

Run a 2-hop traversal from `Graph Engineering` with the hub protected:

```bash
python3 retrieve.py sample_vault "Graph Engineering" --hops 2 --hub-cutoff 4 --show-tokens
```

```
Anchor: Graph Engineering
Vault size: 17 notes
Neighborhood: 6 notes (2 hop(s), hub-cutoff=4)

  - Graph Engineering (anchor)  [230 chars]
  - Harness Engineering  [262 chars]
  - MOC - All Posts  [521 chars]
  - Obsidian Retrieval  [211 chars]
  - Stripe Blueprint  [132 chars]
  - PARA Method  [114 chars]

Approx tokens for this neighborhood: 367
Approx tokens for the whole vault:    949
Reduction: 62%
```

Now run the same traversal without hub protection (`--hub-cutoff 999`) to see
the failure mode the cutoff exists to prevent:

```bash
python3 retrieve.py sample_vault "Graph Engineering" --hops 2 --hub-cutoff 999 --show-tokens
```

```
Neighborhood: 17 notes (2 hop(s), hub-cutoff=999)
...
Reduction: 0%
```

Every unrelated note - bodybuilding, recipes, travel, gift ideas - rides in
through the hub. The cutoff is the difference between a curated neighborhood
and the whole vault.

## How it works

1. `load_vault` walks the directory, parses `[[wikilinks]]` out of every
   markdown file with a regex (no Obsidian install or metadata cache
   required — this works on any linked-markdown corpus, not just a live vault).
2. `build_adjacency` makes the graph bidirectional: if A links to B, B is
   traversable back to A, so backlinks count as much as forward links.
3. `traverse` does a breadth-first walk from the anchor note out to `--hops`
   hops. A note is only excluded from further traversal — not from the
   results — once its own out-degree exceeds `--hub-cutoff`. That's what
   lets a hub note still show up as a direct neighbor without becoming a
   tunnel into the rest of the vault.

## Usage

```bash
python3 retrieve.py <vault_dir> <anchor_note> [--hops N] [--hub-cutoff N] [--show-tokens]
```

- `--hops` (default 2): how many links out from the anchor to include.
- `--hub-cutoff` (default 15): notes with more links than this aren't
  traversed through. Tune this to your vault — a personal vault's MOC notes
  are usually well above this; a small project vault might not need it at all.
- `--show-tokens`: print a rough token estimate (chars / 4) for the retrieved
  neighborhood versus the whole vault, so you can see the actual savings.

## Where this fits

This is the retrieval-layer counterpart to
[examples/graph-engineering-loop-boss-graph.md](../graph-engineering-loop-boss-graph.md):
same claim (declare the topology, don't discover it at runtime), applied to
personal notes instead of multi-agent coordination. See also
[examples/graph-engineering/](../graph-engineering/) for the agent-side version.
