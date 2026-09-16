#!/usr/bin/env python3
"""
retrieve.py - treat an Obsidian vault's [[wikilinks]] as a declared graph
and retrieve context by traversal instead of embedding similarity search.

Usage:
    python3 retrieve.py <vault_dir> <anchor_note> [--hops N] [--hub-cutoff N] [--show-tokens]

No dependencies beyond the standard library.
"""
import argparse
import os
import re
from collections import deque

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def slug(name: str) -> str:
    return name.strip().lower()


def load_vault(vault_dir: str) -> dict:
    """Return {note_slug: {"path", "title", "links": set(slugs), "body"}}."""
    notes = {}
    for root, _, files in os.walk(vault_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            title = f[:-3]
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            links = {slug(m) for m in WIKILINK_RE.findall(text)}
            notes[slug(title)] = {"path": path, "title": title, "links": links, "body": text}
    return notes


def build_adjacency(notes: dict) -> dict:
    """Bidirectional adjacency: forward links plus backlinks."""
    adj = {k: set(v["links"]) for k, v in notes.items()}
    for k, v in notes.items():
        for target in v["links"]:
            if target in adj:
                adj[target].add(k)
    return adj


def traverse(adj: dict, anchor: str, hops: int, hub_cutoff: int) -> list:
    """BFS from anchor, `hops` deep. A note is still included as a direct
    neighbor even if it's a hub, but traversal doesn't continue THROUGH a
    hub past the first hop - that's what keeps one Map-of-Content note
    from pulling in half the vault."""
    visited = {anchor}
    frontier = deque([(anchor, 0)])
    order = [anchor]

    while frontier:
        node, depth = frontier.popleft()
        if depth == hops:
            continue
        if depth > 0 and len(adj.get(node, [])) > hub_cutoff:
            continue  # don't traverse through a hub note
        for neighbor in sorted(adj.get(node, [])):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            order.append(neighbor)
            frontier.append((neighbor, depth + 1))

    return order


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault_dir")
    parser.add_argument("anchor_note")
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--hub-cutoff", type=int, default=15,
                         help="notes with more links than this aren't traversed through")
    parser.add_argument("--show-tokens", action="store_true")
    args = parser.parse_args()

    notes = load_vault(args.vault_dir)
    anchor_slug = slug(args.anchor_note)
    if anchor_slug not in notes:
        raise SystemExit(f"anchor note not found: {args.anchor_note!r}")

    adj = build_adjacency(notes)
    neighborhood = traverse(adj, anchor_slug, args.hops, args.hub_cutoff)

    print(f"Anchor: {notes[anchor_slug]['title']}")
    print(f"Vault size: {len(notes)} notes")
    print(f"Neighborhood: {len(neighborhood)} notes ({args.hops} hop(s), hub-cutoff={args.hub_cutoff})\n")

    total_chars = 0
    for n in neighborhood:
        body_len = len(notes[n]["body"])
        total_chars += body_len
        marker = " (anchor)" if n == anchor_slug else ""
        print(f"  - {notes[n]['title']}{marker}  [{body_len} chars]")

    if args.show_tokens:
        vault_chars = sum(len(v["body"]) for v in notes.values())
        print(f"\nApprox tokens for this neighborhood: {total_chars // 4}")
        print(f"Approx tokens for the whole vault:    {vault_chars // 4}")
        print(f"Reduction: {100 - (100 * total_chars // vault_chars)}%")


if __name__ == "__main__":
    main()
