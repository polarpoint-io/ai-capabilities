# Example: Claude Code Starter Setup for Platform Engineers

**Goal:** A Claude Code setup for platform work that maximises output quality and keeps token spend boring — two files, four repos, a short plugin list, and measurable habits.

Related blog post: [Claude Code for Platform Engineers: The Setup That Doesn't Burn Tokens](https://www.polarpoint.io/blog/2026/07/29/claude-code-for-platform-engineers-the-setup-that-doesnt-burn-tokens/)

See also: [Karpathy's four rules](https://www.polarpoint.io/blog/2026/05/24/the-four-rules-that-make-ai-agents-actually-trustworthy/) · [rolling AGENTS.md out to 40 repos](https://www.polarpoint.io/blog/2026/06/10/your-agentsmd-is-great-now-how-do-you-roll-it-out-to-40-repos/) · [the 6 repos deep-dive](https://www.polarpoint.io/blog/2026/05/26/the-6-github-repos-that-are-redefining-how-ai-agents-think-act-and-talk-to-each-other/)

## Problem

Out of the box, Claude Code has no repo context and expensive habits: re-exploring the same repo structure every session, carrying schema overhead from idle plugins and MCP servers, and producing prose nobody reads. The fix is deciding deliberately what loads always, what loads on demand, and what never loads.

## The context budget

| Tier | What | Cost profile |
|------|------|--------------|
| **Always loaded** | `CLAUDE.md` (behavioural rules) + `AGENTS.md` (repo routing map) | Every session — keep short and universal |
| **On demand** | Skills (procedures, checklists, runbooks) | Free until invoked — as detailed as you like |
| **Per session** | Plugins + connected MCP server schemas | Silent overhead at session start — audit monthly |

## Setup checklist (the first hour)

1. **CLAUDE.md** (30 min): start from [`templates/CLAUDE.md`](../templates/CLAUDE.md) — Karpathy's four rules extended with blast-radius awareness and approval tiers. Add your three most-violated repo conventions.
2. **AGENTS.md** (20 min): routing map for your main GitOps repo — what lives where, which docs cover what. Base: [`platform-standards/`](../platform-standards/) default template. Validate with [`agentsmd-validator`](../agentsmd-validator/).
3. **Disconnect idle MCP servers** (10 min): every connected server ships its tool schemas into context at session start.

## The four repos

| Repo | Why |
|------|-----|
| `andrej-karpathy-skills` | The 65-line CLAUDE.md discipline base (41% → 11% measured error reduction) |
| `superpowers` | ~30 pre-built skills; community benchmarks: ~14% fewer tokens with better output |
| `everything-claude-code` | Persistence: background tasks, checkpoints, parallel work for long platform tasks |
| `ai-capabilities` (this repo) | Platform-extended CLAUDE.md, AGENTS.md with approval tiers, agent-task issue template |

## Token discipline habits

- **Scope like a ticket**: "refactor the login function in auth.ts", not "refactor auth"
- **`/recap`** on resume instead of replaying scrollback
- **`ENABLE_PROMPT_CACHING_1H`** for long working sessions
- **Model per task**: cheap tier for routine YAML/summaries, heavyweight for architecture and debugging
- **Measure first**: audit token usage before installing optimisation plugins — most spend traces to repo re-exploration a better AGENTS.md fixes for free

## First skills to create

1. "Add a new service to the golden path" — encodes your conventions
2. "Run the deploy checklist" — encodes your gates
3. "Draft the incident update" — encodes your comms format
