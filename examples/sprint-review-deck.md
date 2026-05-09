# Example: Sprint Review Deck (Marp)

**Goal:** Generate a review deck from metrics using AGENTS.md.

## Two parts of the review
- **Platform development** — project‑shaped work (objectives, demos, milestones). Human‑written slides.
- **BAU and operations** — ticket‑shaped work (request counts, SLA, resolution trends). Agent‑populated slides.

## Metrics to include
- Number of requests by category
- Resolution time trends
- SLA compliance
- Top requesting teams
- Request complexity distribution

## Output
- `/scripts/marp/output/sprint-review.md`
- `/scripts/marp/output/sprint-review.html`

## Agent Prompts
- Surveyor: extract metrics
- Writer: compose slides
- Coder: generate deck

