#!/usr/bin/env python3
"""
vault-processor.py — Process an Obsidian PARA vault inbox using Claude.

Usage:
    # Read vault from filesystem
    ANTHROPIC_API_KEY=<key> python scripts/obsidian/vault-processor.py \
        --vault ~/Documents/Obsidian/MyVault

    # Read/write via Obsidian Local REST API plugin
    ANTHROPIC_API_KEY=<key> OBSIDIAN_API_TOKEN=<token> \
        python scripts/obsidian/vault-processor.py --use-rest-api

    # Weekly area review
    ANTHROPIC_API_KEY=<key> python scripts/obsidian/vault-processor.py \
        --vault ~/Documents/Obsidian/MyVault \
        --mode area-review --area Health

Environment variables:
    ANTHROPIC_API_KEY       Required
    OBSIDIAN_VAULT_PATH     Path to vault root (or pass --vault)
    OBSIDIAN_API_TOKEN      Only needed with --use-rest-api
    OBSIDIAN_API_PORT       Default: 27123

Output:
    Processing report to stdout.
    Exit code 0 = success, 1 = error.

Requires:
    pip install anthropic requests
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import date
from typing import Optional

import anthropic

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Vault access — filesystem or Local REST API
# ---------------------------------------------------------------------------

def read_file_fs(vault: Path, relative_path: str) -> str:
    """Read a note from the vault filesystem."""
    full_path = vault / relative_path
    if not full_path.exists():
        return ""
    return full_path.read_text(encoding="utf-8")


def read_file_api(base_url: str, headers: dict, relative_path: str) -> str:
    """Read a note via the Obsidian Local REST API."""
    resp = requests.get(
        f"{base_url}/vault/{relative_path}",
        headers=headers,
    )
    if resp.status_code == 404:
        return ""
    resp.raise_for_status()
    return resp.json().get("content", "")


def list_files_api(base_url: str, headers: dict, folder: str) -> list[str]:
    """List files in a vault folder via the Local REST API."""
    resp = requests.get(f"{base_url}/vault/{folder}/", headers=headers)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return [f for f in data.get("files", []) if f.endswith(".md")]


def list_files_fs(vault: Path, folder: str) -> list[str]:
    """List markdown files in a vault folder."""
    folder_path = vault / folder
    if not folder_path.exists():
        return []
    return [str(p.relative_to(vault)) for p in folder_path.rglob("*.md")]


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------

def load_system_prompt(read_fn) -> str:
    return read_fn("_system-prompt.md")


def load_active_project_contexts(read_fn, list_fn) -> str:
    """Load _context.md from each active project folder."""
    projects = list_fn("Projects")
    contexts = []
    for file_path in projects:
        if file_path.endswith("_context.md"):
            project_name = Path(file_path).parent.name
            content = read_fn(file_path)
            if content.strip():
                contexts.append(f"## Project: {project_name}\n\n{content}")
    return "\n\n".join(contexts)


def load_inbox(read_fn) -> str:
    return read_fn("00 Inbox.md")


# ---------------------------------------------------------------------------
# Processing prompts
# ---------------------------------------------------------------------------

INBOX_PROCESSOR_PROMPT = """You are processing an Obsidian PARA vault inbox.

For each item in the inbox, output a structured processing report. Each item should include:
- What type of content it is (meeting note, article, idea, action, reference, etc.)
- Which PARA bucket it belongs in: Projects / Areas / Resources / Archive
- A suggested file path within that bucket (e.g. "Projects/Platform Migration Q3/2026-05-04 standup.md")
- Any action items extracted (as [ ] checkboxes)
- Suggested links to existing notes (use [[wiki-link]] format)
- A brief summary (2-3 sentences) if the item is long

Format your response as:

## Inbox Processing — {date}

### Item N: "<first few words of the item>"
- **Type**: [content type]
- **PARA bucket**: [bucket name]
- **Suggested path**: `[file path]`
- **Actions extracted**:
  - [ ] [action 1]
  - [ ] [action 2]
- **Suggested links**: [[link1]], [[link2]]
- **Summary**: [brief summary if needed]

---

If the inbox is empty, say so briefly.
If an item is ambiguous between Projects and Areas, explain why and give a recommendation.
""".replace("{date}", date.today().isoformat())


AREA_REVIEW_PROMPT = """You are reviewing an Obsidian PARA area. Read the overview and log carefully.

Produce a structured review:

## Area Review: {area} — {date}

### Commitments not followed through
[List any commitments from the log that appear unresolved]

### Patterns noticed
[2-3 patterns or themes visible across the log entries]

### Highest-impact focus for this week
[One specific, concrete action with the most leverage — not a vague suggestion]

### What to track next
[1-2 things worth logging over the coming weeks to see if they improve]

Be direct. Don't soften the patterns you see. The goal is useful reflection, not comfort.
"""


# ---------------------------------------------------------------------------
# Core processing functions
# ---------------------------------------------------------------------------

def process_inbox(client: anthropic.Anthropic, system_context: str, inbox: str) -> str:
    """Run inbox processing against Claude."""
    if not inbox.strip():
        return f"## Inbox Processing — {date.today().isoformat()}\n\nInbox is empty. Nothing to process."

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=system_context,
        messages=[
            {
                "role": "user",
                "content": f"{INBOX_PROCESSOR_PROMPT}\n\nHere is the inbox content:\n\n{inbox}",
            }
        ],
    )
    return message.content[0].text


def process_area_review(
    client: anthropic.Anthropic, system_context: str, area: str, overview: str, log: str
) -> str:
    """Run a weekly area review against Claude."""
    prompt = AREA_REVIEW_PROMPT.replace("{area}", area).replace("{date}", date.today().isoformat())

    area_content = f"## Overview\n\n{overview}\n\n## Log\n\n{log}"

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=system_context,
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\nArea notes:\n\n{area_content}",
            }
        ],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Process Obsidian PARA vault with Claude")
    parser.add_argument("--vault", help="Path to vault root (or set OBSIDIAN_VAULT_PATH)")
    parser.add_argument(
        "--use-rest-api",
        action="store_true",
        help="Use Obsidian Local REST API instead of filesystem",
    )
    parser.add_argument(
        "--mode",
        choices=["inbox", "area-review"],
        default="inbox",
        help="Processing mode (default: inbox)",
    )
    parser.add_argument("--area", help="Area name for area-review mode")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OBSIDIAN_API_PORT", "27123")),
        help="Local REST API port (default: 27123)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable required", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Set up read functions
    if args.use_rest_api:
        if not HAS_REQUESTS:
            print("Error: 'requests' package required for REST API mode. pip install requests", file=sys.stderr)
            sys.exit(1)

        token = os.environ.get("OBSIDIAN_API_TOKEN")
        if not token:
            print("Error: OBSIDIAN_API_TOKEN required for --use-rest-api", file=sys.stderr)
            sys.exit(1)

        base_url = f"http://localhost:{args.port}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        read_fn = lambda path: read_file_api(base_url, headers, path)
        list_fn = lambda folder: list_files_api(base_url, headers, folder)

    else:
        vault_path = args.vault or os.environ.get("OBSIDIAN_VAULT_PATH")
        if not vault_path:
            print(
                "Error: --vault or OBSIDIAN_VAULT_PATH required (or use --use-rest-api)",
                file=sys.stderr,
            )
            sys.exit(1)

        vault = Path(vault_path).expanduser()
        if not vault.exists():
            print(f"Error: vault path does not exist: {vault}", file=sys.stderr)
            sys.exit(1)

        read_fn = lambda path: read_file_fs(vault, path)
        list_fn = lambda folder: list_files_fs(vault, folder)

    # Build system context
    system_prompt = load_system_prompt(read_fn)
    project_contexts = load_active_project_contexts(read_fn, list_fn)

    system_context = system_prompt
    if project_contexts:
        system_context += f"\n\n# Active Project Contexts\n\n{project_contexts}"

    if not system_context.strip():
        system_context = (
            "You are a personal knowledge assistant working within an Obsidian PARA vault. "
            "You help process, organise, retrieve, and synthesise notes. "
            "Be direct and concise. Cite specific notes when relevant."
        )

    # Run the selected mode
    if args.mode == "inbox":
        inbox = load_inbox(read_fn)
        result = process_inbox(client, system_context, inbox)

    elif args.mode == "area-review":
        if not args.area:
            print("Error: --area required for area-review mode", file=sys.stderr)
            sys.exit(1)

        overview = read_fn(f"Areas/{args.area}/_overview.md")
        log = read_fn(f"Areas/{args.area}/_log.md")

        if not overview and not log:
            print(f"Error: no overview or log found for area: {args.area}", file=sys.stderr)
            sys.exit(1)

        result = process_area_review(client, system_context, args.area, overview, log)

    print(result)


if __name__ == "__main__":
    main()
