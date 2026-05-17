# Sprint Review Agents — GitHub Projects

## Configuration

```yaml
owner: "YourOrg"
repo: "your-repo"
project_number: 1          # GitHub Projects v2 project number
sprint_duration_days: 14
tracker: github
```

Label conventions assumed by these agents:
- Request type/category: `type:infra`, `type:security`, `type:access`, etc.
- Complexity: `complexity:simple`, `complexity:medium`, `complexity:complex`
- Requesting team: `team:backend`, `team:data`, `team:frontend`, etc.
- Blocked: `blocked`, `impediment`

These values are substituted into every GraphQL query via `@Owner`, `@Repo`, and `@StartDate`. Change them once here; all agents pick them up.

> **Note:** GitHub Projects v2 stores custom fields (Points, Complexity, Team) per-project. Adjust field names in each agent to match what you've defined in your project board.

---

## Master Agent: Populate All Slides and Diagrams

```
You are coordinating a sprint review deck update.

Steps:
1. Calculate @StartDate as today minus 14 days (ISO 8601 format)
2. Set @Owner and @Repo from the configuration block above
3. Ask the user: "Ready to query GitHub and update the deck. Proceed? (y/n)"
4. If yes, run agents in this order:
   - Agent 1: Request Counts by Category
   - Agent 2: Resolution Time Trends
   - Agent 3: SLA Compliance
   - Agent 4: Request Complexity Distribution
   - Agent 5: Requestor Patterns
   - Agent 6: Request Metrics Summary (arithmetic — runs after 1–5)
   - Agent 7: Platform Development Summary (template only — no GitHub query)
   - Agent 8: Key Insights (comparative — runs after 6)
   - Agent 9: Next Sprint Objectives (template only — prompts for input)
5. After all agents complete, report a summary of what was updated
6. Suggest running: make diagrams && make html
```

---

## Agent 1: Request Counts by Category

**Updates:** `diagrams/request-distribution.puml`

```
Query GitHub Issues labelled as requests created in the last 14 days.

GraphQL:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["request"], since: "@StartDate" }) {
      nodes {
        title
        labels { nodes { name } }
        createdAt
        state
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. For each issue, extract the type label (prefix "type:") as the category
   If no type label, group under "Uncategorised"
3. Count issues per category
4. Update the bar data array in diagrams/request-distribution.puml:
   Replace each "Category" N line with the new count
5. Preserve all other lines in the file
```

---

## Agent 2: Resolution Time Trends

**Updates:** `diagrams/resolution-time-trends.puml`

```
Query GitHub for closed request issues and calculate daily average resolution time.

GraphQL:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["request"], since: "@StartDate" }, states: CLOSED) {
      nodes {
        createdAt
        closedAt
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. For each issue, calculate resolution days = closedAt - createdAt
3. Group by day (createdAt date part), average resolution days per day
4. Update the line chart data points in diagrams/resolution-time-trends.puml
5. Format dates as DD/MM for the axis labels
```

---

## Agent 3: SLA Compliance

**Updates:** `deck.md` — "SLA Compliance" table in the Operations Overview slide

```
Query GitHub for all request issues and check SLA thresholds.

SLA thresholds (adjust to match your team's targets):
  Simple requests (complexity:simple): 2 business days
  Medium requests (complexity:medium): 5 business days
  Complex requests (complexity:complex): 10 business days

GraphQL:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["request"], since: "@StartDate" }) {
      nodes {
        labels { nodes { name } }
        createdAt
        closedAt
        state
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. For each closed issue, read the complexity label to determine the SLA threshold
3. Check if resolution time (closedAt - createdAt) <= threshold
4. Calculate: met_sla / total_closed * 100 = compliance %
5. Update the SLA row in the Operations Overview table in deck.md
```

---

## Agent 4: Request Complexity Distribution

**Updates:** `diagrams/request-complexity.puml`

```
Query GitHub for request issues and group by complexity label.

GraphQL:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["request"], since: "@StartDate" }) {
      nodes {
        labels { nodes { name } }
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. Count issues with label complexity:simple, complexity:medium, complexity:complex
3. Issues with no complexity label: group under "Uncategorised"
4. Update the three bar values in diagrams/request-complexity.puml
```

---

## Agent 5: Requestor Patterns

**Updates:** `diagrams/requestor-patterns.puml`

```
Query GitHub for request issues and group by requesting team label.

GraphQL:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["request"], since: "@StartDate" }) {
      nodes {
        labels { nodes { name } }
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. For each issue, extract the team label (prefix "team:") as the requestor
   If no team label, group under "Unknown"
3. Count requests per team, sort descending, take top 5
4. Update the bar data array in diagrams/requestor-patterns.puml with the top 5
5. If fewer than 5 teams, fill remaining bars with count 0
```

---

## Agent 6: Request Metrics Summary

**Updates:** `deck.md` — Operations Overview slide metrics table

```
This agent does arithmetic on the data already collected by Agents 1–5.
No GitHub query needed — use the counts from previous agents.

Steps:
1. Sum all category counts from Agent 1 → total requests this sprint
2. Calculate average resolution time from Agent 2 data → avg days
3. Read SLA compliance % from Agent 3 → compliance figure
4. Identify peak request day from Agent 2 daily data
5. Update the Operations Overview table in deck.md:

| Metric | This Sprint | Previous Sprint |
|--------|-------------|-----------------|
| Total requests | [new total] | [previous total] |
| Avg resolution (days) | [new avg] | [previous avg] |
| SLA compliance | [new %] | [previous %] |
| Peak request day | [date] | [date] |

For 'Previous Sprint' values: read from the existing table before overwriting.
```

---

## Agent 7: Platform Development Summary

**Updates:** `deck.md` — Platform Development slide (template prompts only)

```
This agent does not query GitHub. It outputs a slide template and prompts the
team to fill in the narrative sections.

Steps:
1. Locate the "Platform Development" slide in deck.md
2. If it contains placeholder text from last sprint, clear the bullet content
3. Output this prompt to the user:

"Platform Development slide is ready. Please fill in:
 - Objectives met this sprint:
 - Objectives slipped and why:
 - Demo or deliverable to show:
 - Key decision or learning:"

4. Wait for user input and write it into the slide
```

---

## Agent 8: Key Insights

**Updates:** `deck.md` — Key Insights slide

```
Compare this sprint's figures against previous sprint using the Operations
Overview table (which Agent 6 has already updated with both columns).

Steps:
1. Read current and previous sprint figures from the Operations Overview table
2. Calculate deltas: resolution time change, SLA change, volume change
3. Identify the most significant trend (positive or negative)
4. Write 3–4 data-backed bullet points into the Key Insights slide in deck.md:

Format:
- Requests [up/down] X% vs last sprint ([N] → [N])
- Avg resolution time [improved/worsened] by Y days ([prev] → [curr])
- SLA compliance [held/improved/dropped] at Z%
- [Callout]: [most interesting specific observation]

5. Keep the language factual — do not editorialize
```

---

## Agent 9: Next Sprint Objectives

**Updates:** `deck.md` — Next Sprint slide

```
This agent does not query GitHub. It clears the previous sprint's objectives
and prompts for the new ones.

Steps:
1. Locate the "Next Sprint" slide in deck.md
2. Clear the existing bullet points
3. Output this prompt to the user:

"Next Sprint slide is ready. Please provide:
 - Platform development objective 1:
 - Platform development objective 2:
 - Any BAU focus areas or SLA targets to call out:
 - Dependencies or risks to flag:"

4. Wait for user input and write it into the slide
```

---

## Master Agent (Scrum Master / Product Mode): Sprint Health Check

Run this instead of — or after — the platform operations Master Agent when you want the product and delivery view.

```
You are coordinating the scrum master / product owner section of the sprint review.

Steps:
1. Calculate @StartDate as today minus 14 days (ISO 8601 format)
2. Set @Owner and @Repo from the configuration block above
3. Ask the user: "Ready to run the product/scrum health check? (y/n)"
4. If yes, run agents in this order:
   - Agent 10: Sprint Goal Assessment
   - Agent 11: Impediment Summary
   - Agent 12: Backlog Readiness (next sprint)
   - Agent 13: Velocity Tracker
5. After all agents complete, write a 4-line "Sprint Health" summary at the
   top of the Key Insights slide in deck.md (before the metrics bullets):

   Sprint goal: [met / partially met / not met] — [one sentence why]
   Velocity: [N points] ([+/-X] vs sprint average)
   Blockers resolved: [N] open, [N] cleared this sprint
   Next sprint ready: [N items] meeting Definition of Ready

6. Suggest: "Review the completed deck with: make html"
```

---

## Agent 10: Sprint Goal Assessment

**Updates:** `deck.md` — Sprint Goal status line in Key Insights slide

```
Assess whether the sprint goal was achieved based on issue completion.

GraphQL — closed issues this sprint:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { since: "@StartDate" }, states: CLOSED) {
      nodes {
        title
        closedAt
        labels { nodes { name } }
        milestone { title }
      }
    }
  }
}

GraphQL — open issues (committed but not closed):
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { since: "@StartDate" }, states: OPEN) {
      nodes {
        title
        labels { nodes { name } }
        milestone { title }
      }
    }
  }
}

Steps:
1. Run both queries, filter to issues in the current sprint milestone
2. Calculate: completion rate = closed / (closed + open) * 100
3. Rate the sprint goal:
   - >= 80% closed → "met"
   - 50–79% → "partially met"
   - < 50% → "not met"
4. Prompt: "What was the sprint goal this sprint?" — accept one sentence from user
5. Write to Key Insights slide in deck.md:
   Sprint goal: [status] — [user-provided goal sentence]
   Completion rate: [N]% ([closed] of [total] issues)
```

---

## Agent 11: Impediment Summary

**Updates:** `deck.md` — Impediments section in Key Insights slide

```
Surface open blockers and impediments so they can be raised in the review.

GraphQL — blocked issues:
{
  repository(owner: "@Owner", name: "@Repo") {
    issues(first: 100, filterBy: { labels: ["blocked"] }, states: OPEN) {
      nodes {
        title
        createdAt
        assignees { nodes { login } }
        labels { nodes { name } }
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. Group results:
   a. Resolved this sprint (closed between @StartDate and today)
   b. Still open as of today
3. For open impediments older than 5 days, flag as "escalation candidate"
4. Write to Key Insights slide in deck.md:

   Impediments:
   - Cleared this sprint: [N]
   - Still open: [N] ([list titles of open items, one per line])
   - Escalation candidates (>5 days open): [titles, assigned to, age in days]

5. If no blocked issues found, write: "No open impediments recorded in GitHub."
```

---

## Agent 12: Backlog Readiness

**Updates:** `deck.md` — Next Sprint slide, Readiness section

```
Check that issues planned for next sprint meet the Definition of Ready.

Definition of Ready checklist (adjust to your team's standards):
  - Has a body / description (non-empty)
  - Has a Points or Estimate project field value (not 0 or null)
  - Is assigned to a milestone
  - Is not labelled "blocked"

GraphQL — next sprint candidates (open issues in next milestone):
{
  repository(owner: "@Owner", name: "@Repo") {
    milestones(first: 5, orderBy: { field: DUE_DATE, direction: ASC }) {
      nodes {
        title
        dueOn
        issues(first: 50, states: OPEN) {
          nodes {
            title
            body
            assignees { nodes { login } }
            labels { nodes { name } }
            milestone { title }
          }
        }
      }
    }
  }
}

Steps:
1. Run the query, select the next-upcoming milestone
2. For each issue, check each DoR criterion — mark pass/fail
3. Count: [N] of [total] issues meet all DoR criteria
4. List issues failing DoR with the specific missing fields
5. Update the Next Sprint slide in deck.md:

   Backlog readiness:
   - [N] of [total] issues ready for sprint planning
   - Not ready: [list titles + missing fields]

6. Prompt: "Do you want me to add a comment to the failing issues in GitHub? (y/n)"
   If yes, add a comment to each failing issue listing the missing fields.
```

---

## Agent 13: Velocity Tracker

**Updates:** `deck.md` — Operations Overview slide, Velocity row

```
Calculate sprint velocity and 4-sprint rolling average using GitHub milestone data.

GraphQL — closed issues with Points field, last 4 milestones:
{
  repository(owner: "@Owner", name: "@Repo") {
    milestones(last: 4, states: CLOSED) {
      nodes {
        title
        issues(first: 100, states: CLOSED) {
          nodes {
            title
            projectItems(first: 1) {
              nodes {
                fieldValueByName(name: "Points") {
                  ... on ProjectV2ItemFieldNumberValue { number }
                }
              }
            }
          }
        }
      }
    }
  }
}

Steps:
1. Run the GraphQL query
2. For each milestone, sum the Points field values across closed issues
3. Identify this sprint and the three before it
4. Calculate:
   - This sprint velocity: sum of points in current milestone
   - 4-sprint rolling average: mean of last 4 milestones
   - Delta vs average: this sprint - rolling average
5. Update the Operations Overview table in deck.md, adding a Velocity row:

   | Velocity (points) | [this sprint] | [rolling avg] |

6. Write a one-line trend note for the Key Insights slide:
   Velocity: [N] points ([+/-X] vs 4-sprint avg of [avg])

Note: If your project doesn't use a Points field, substitute issue count as a
proxy for velocity — adjust the query to remove the projectItems field lookup.
```
