# Example: Obsidian Vault Processor

**Goal:** Connect your Obsidian PARA vault to Claude so the LLM can process your inbox, categorise notes, suggest links, and load active project context — automatically.

Related blog post: [Your Second Brain, Now With an AI Inside It](/blog/2026/05/04/your-second-brain-now-with-an-ai-inside-it/)

## Problem

An Obsidian vault with PARA gives you a searchable, linkable second brain. But processing the inbox — deciding where things go, extracting actions, linking to existing notes — still requires mental energy at the end of a long day. An LLM can do all of it in one prompt.

## Workflow

1. **Load context**: read your `_system-prompt.md` and active `Projects/*/\_context.md` files
2. **Read inbox**: pull the full contents of `00 Inbox.md`
3. **Process**: Claude categorises each item (PARA bucket), extracts actions, suggests links
4. **Review**: processing report posted to stdout — approve suggestions before applying
5. **Optional**: use the Local REST API to write categorised notes directly back to the vault

## Vault structure expected

```
vault/
├── 00 Inbox.md              ← everything goes here first
├── _system-prompt.md        ← your LLM OS instructions
├── Projects/
│   └── <project>/
│       └── _context.md      ← current state, decisions, open questions
├── Areas/
│   └── <area>/
│       ├── _overview.md
│       └── _log.md
├── Resources/               ← reference material
└── Archive/                 ← completed / inactive
```

## Scripts

```bash
# Process inbox with manual vault path (no plugin needed)
ANTHROPIC_API_KEY=<key> python scripts/obsidian/vault-processor.py \
  --vault ~/path/to/your/vault

# Run with Obsidian Local REST API (live vault read/write)
ANTHROPIC_API_KEY=<key> OBSIDIAN_API_TOKEN=<token> \
  python scripts/obsidian/vault-processor.py --use-rest-api

# Weekly area review for a specific area
ANTHROPIC_API_KEY=<key> python scripts/obsidian/vault-processor.py \
  --vault ~/path/to/your/vault --mode area-review --area Health
```

## Environment variables required

```bash
ANTHROPIC_API_KEY=<key>
OBSIDIAN_VAULT_PATH=~/Documents/Obsidian/MyVault   # or pass --vault
OBSIDIAN_API_TOKEN=<token>                          # only if using Local REST API
OBSIDIAN_API_PORT=27123                             # default
```

## Inputs

- `00 Inbox.md` — raw captures (text, links, voice transcriptions, meeting notes)
- `_system-prompt.md` — LLM OS system prompt with your rules and preferences
- `Projects/*/\_context.md` — active project context files (current state, open questions)

## Outputs

- **Processing report** (stdout): per-item PARA categorisation, extracted actions, suggested links
- **Optional**: new notes written directly to vault via Local REST API

## Processing report format

```
## Inbox Processing — 2026-05-04

### Item 1: "Notes from platform meeting"
- **Type**: Meeting notes
- **PARA bucket**: Projects/Platform Migration Q3
- **Actions extracted**:
  - [ ] Follow up with Sarah on Crossplane 2.2 upgrade timing
  - [ ] Check vendor contract renewal status with Tom
- **Suggested links**: [[ADR-004]], [[Platform Migration Q3/_context]]
- **File as**: `Projects/Platform Migration Q3/2026-05-04 platform meeting.md`

### Item 2: "Article on Kubernetes cost optimisation"
- **Type**: Resource
- **PARA bucket**: Resources/Kubernetes
- **Actions extracted**: none
- **Suggested links**: [[Resources/FinOps/cloud-cost-baseline]]
- **File as**: `Resources/Kubernetes/k8s-cost-optimisation.md`
```

## Agent prompts

- **Inbox Processor**: categorise each inbox item into PARA, extract actions, identify links to existing notes
- **Area Reviewer**: surface unmet commitments, patterns, and high-impact focus for the week
- **Context Loader**: read project context files and build a session-aware system prompt

## Obsidian Local REST API setup

Install the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) community plugin in Obsidian. Enable it in Settings → Community Plugins. Copy the API key from the plugin settings into `OBSIDIAN_API_TOKEN`.

The API runs on `localhost:27123` by default and exposes your vault over HTTP — no cloud, no sync service, fully local.
