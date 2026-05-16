# Example: Sprint Review Deck (Marp + AGENTS.md)

**Goal:** Generate a sprint review deck from ADO metrics using a nine-agent AGENTS.md workflow — operations slides populated automatically, platform development slides templated for manual input.

Related blog post: [Sprint Reviews with Marp: Presentations as Code](https://www.polarpoint.io/blog/2026/03/29/sprint-reviews-with-marp-presentations-as-code/)

## Two parts of the review

Platform engineering sprint reviews split into two distinct types of content:

- **Platform development** — project-shaped work (objectives, milestones, design decisions, demos). Human-written each sprint. Agents produce a template and prompt for input.
- **BAU and operations** — ticket-shaped work (request counts, SLA, resolution trends). Agent-populated from ADO data. Numbers change every sprint; format does not.

## Nine-agent workflow

| Agent | Role | Output |
|-------|------|--------|
| Agent 1 | Request counts by category | `diagrams/request-distribution.puml` |
| Agent 2 | Resolution time trends (14-day daily avg) | `diagrams/resolution-time-trends.puml` |
| Agent 3 | SLA compliance by complexity | `deck.md` — SLA row in Operations table |
| Agent 4 | Request complexity distribution | `diagrams/request-complexity.puml` |
| Agent 5 | Top requesting teams | `diagrams/requestor-patterns.puml` |
| Agent 6 | Operations metrics summary (arithmetic) | `deck.md` — Operations Overview table |
| Agent 7 | Platform development template | `deck.md` — Platform Development slide |
| Agent 8 | Key insights (sprint-over-sprint comparison) | `deck.md` — Key Insights slide |
| Agent 9 | Next sprint objectives template | `deck.md` — Next Sprint slide |

A Master Agent orchestrates all nine in sequence with a single prompt: `"Run Master Agent: Populate All Diagrams and Slides"`.

## Files

```
scripts/marp/
├── agents.md                    # Nine-agent workflow + Master Agent
├── deck.md                      # Slide template (update each sprint)
├── Makefile                     # make all | diagrams | html | pdf | pptx
├── generate-deck.sh             # Demo script using local sample data
└── diagrams/
    ├── request-distribution.puml
    └── requestor-patterns.puml
```

## Workflow

```bash
# 1. Configure your ADO area path in agents.md
# 2. Run the master agent in VS Code Copilot:
#    "Run Master Agent: Populate All Diagrams and Slides"
# 3. Generate PNG charts
make diagrams
# 4. Preview the deck
make html
# 5. Export for stakeholders
make pdf
make pptx
```

## Demo (local sample data)

```bash
./scripts/marp/generate-deck.sh
# Reads from scripts/metrics/sample-data.json
# Outputs scripts/marp/output/sprint-review.md (and .html if marp-cli is installed)
```

## Inputs

- ADO area path configured in `agents.md`
- Work items of type `Request` with `Custom.RequestComplexity` and `Custom.RequestedTeamName` fields
- PlantUML snapshot JAR at `~/tools/plantuml-snapshot.jar`
- marp-cli installed (`npm install -g @marp-team/marp-cli`)

## Outputs

- `deck.md` — updated with current sprint metrics
- `diagrams/*.png` — PlantUML charts regenerated
- `output/sprint-review.html` — browser-ready deck for presenting
- `output/sprint-review.pdf` — print-ready for archiving
- `output/sprint-review.pptx` — PowerPoint for stakeholders
