# Sprint Review Agents

## Configuration

```yaml
area_path: "YourOrg\\YourProject\\Platform Engineering"
sprint_duration_days: 14
tracker: ado  # ado | github | jira
```

These values are substituted into every WIQL query via `@AreaPath` and `@StartDate`. Change them once here; all agents pick them up.

---

## Master Agent: Populate All Slides and Diagrams

```
You are coordinating a sprint review deck update.

Steps:
1. Calculate @StartDate as today minus 14 days (ISO 8601 format)
2. Set @AreaPath from configuration block above
3. Ask the user: "Ready to query ADO and update the deck. Proceed? (y/n)"
4. If yes, run agents in this order:
   - Agent 1: Request Counts by Category
   - Agent 2: Resolution Time Trends
   - Agent 3: SLA Compliance
   - Agent 4: Request Complexity Distribution
   - Agent 5: Requestor Patterns
   - Agent 6: Request Metrics Summary (arithmetic — runs after 1–5)
   - Agent 7: Platform Development Summary (template only — no ADO query)
   - Agent 8: Key Insights (comparative — runs after 6)
   - Agent 9: Next Sprint Objectives (template only — prompts for input)
5. After all agents complete, report a summary of what was updated
6. Suggest running: make diagrams && make html
```

---

## Agent 1: Request Counts by Category

**Updates:** `diagrams/request-distribution.puml`

```
Query ADO for all work items of type 'Request' in the last 14 days.

WIQL:
SELECT [System.Id], [System.Title], [System.Tags]
FROM WorkItems
WHERE [System.WorkItemType] = 'Request'
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.CreatedDate] >= '@StartDate'

Steps:
1. Run the WIQL query
2. Group results by [System.Tags] (primary tag = category)
3. Count items per category
4. Update the bar data array in diagrams/request-distribution.puml:
   Replace each "Category" N line with the new count
5. Preserve all other lines in the file
```

---

## Agent 2: Resolution Time Trends

**Updates:** `diagrams/resolution-time-trends.puml`

```
Query ADO for completed Requests and calculate daily average resolution time.

WIQL:
SELECT [System.Id], [System.CreatedDate], [Microsoft.VSTS.Common.ClosedDate]
FROM WorkItems
WHERE [System.WorkItemType] = 'Request'
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] = 'Closed'
  AND [System.CreatedDate] >= '@StartDate'

Steps:
1. Run the WIQL query
2. For each item, calculate resolution days = ClosedDate - CreatedDate
3. Group by day (CreatedDate date part), average resolution days per day
4. Update the line chart data points in diagrams/resolution-time-trends.puml
5. Format dates as DD/MM for the axis labels
```

---

## Agent 3: SLA Compliance

**Updates:** `deck.md` — "SLA Compliance" table in the Operations Overview slide

```
Query ADO for all Requests and check SLA thresholds.

SLA thresholds (adjust to match your team's targets):
  Simple requests: 2 business days
  Medium requests: 5 business days
  Complex requests: 10 business days

WIQL:
SELECT [System.Id], [System.CreatedDate], [Microsoft.VSTS.Common.ClosedDate],
       [Custom.RequestComplexity]
FROM WorkItems
WHERE [System.WorkItemType] = 'Request'
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.CreatedDate] >= '@StartDate'

Steps:
1. Run the WIQL query
2. For each closed item, check if resolution time <= threshold for its complexity
3. Calculate: met_sla / total_closed * 100 = compliance %
4. Update the SLA row in the Operations Overview table in deck.md
```

---

## Agent 4: Request Complexity Distribution

**Updates:** `diagrams/request-complexity.puml`

```
Query ADO for Requests and group by complexity.

WIQL:
SELECT [System.Id], [Custom.RequestComplexity]
FROM WorkItems
WHERE [System.WorkItemType] = 'Request'
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.CreatedDate] >= '@StartDate'

Steps:
1. Run the WIQL query
2. Count items with Custom.RequestComplexity = 'Simple', 'Medium', 'Complex'
3. Update the three bar values in diagrams/request-complexity.puml
```

---

## Agent 5: Requestor Patterns

**Updates:** `diagrams/requestor-patterns.puml`

```
Query ADO for all Requests and group by requesting team.

WIQL:
SELECT [System.Id], [Custom.RequestedTeamName]
FROM WorkItems
WHERE [System.WorkItemType] = 'Request'
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.CreatedDate] >= '@StartDate'

Steps:
1. Run the WIQL query
2. Group by Custom.RequestedTeamName, count requests per team
3. Sort descending, take top 5
4. Update the bar data array in diagrams/requestor-patterns.puml with the top 5
5. If fewer than 5 teams, fill remaining bars with count 0
```

---

## Agent 6: Request Metrics Summary

**Updates:** `deck.md` — Operations Overview slide metrics table

```
This agent does arithmetic on the data already collected by Agents 1–5.
No ADO query needed — use the counts from previous agents.

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
This agent does not query ADO. It outputs a slide template and prompts the
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
This agent does not query ADO. It clears the previous sprint's objectives
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
2. Set @AreaPath from configuration block above
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
Assess whether the sprint goal was achieved based on work item completion.

WIQL — completed items this sprint:
SELECT [System.Id], [System.Title], [System.State], [System.Tags],
       [Microsoft.VSTS.Common.ClosedDate]
FROM WorkItems
WHERE [System.WorkItemType] IN ('User Story', 'Task', 'Request')
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] IN ('Closed', 'Done', 'Resolved')
  AND [Microsoft.VSTS.Common.ClosedDate] >= '@StartDate'

WIQL — all committed items (created before sprint start, not closed):
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] IN ('User Story', 'Task', 'Request')
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] NOT IN ('Closed', 'Done', 'Resolved')
  AND [System.CreatedDate] < '@StartDate'

Steps:
1. Run both queries
2. Calculate: completion rate = closed / (closed + open committed) * 100
3. Rate the sprint goal:
   - >= 80% closed → "met"
   - 50–79% → "partially met"
   - < 50% → "not met"
4. Prompt: "What was the sprint goal this sprint?" — accept one sentence from user
5. Write to Key Insights slide in deck.md:
   Sprint goal: [status] — [user-provided goal sentence]
   Completion rate: [N]% ([closed] of [total] items)
```

---

## Agent 11: Impediment Summary

**Updates:** `deck.md` — Impediments section in Key Insights slide

```
Surface open blockers and impediments so they can be raised in the review.

WIQL — blocked items (tagged or in a blocked state):
SELECT [System.Id], [System.Title], [System.State], [System.Tags],
       [System.AssignedTo], [System.CreatedDate]
FROM WorkItems
WHERE [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] NOT IN ('Closed', 'Done', 'Resolved')
  AND (
    [System.Tags] CONTAINS 'blocked'
    OR [System.Tags] CONTAINS 'impediment'
    OR [System.BoardLane] = 'Blocked'
  )

Steps:
1. Run the WIQL query
2. Group results:
   a. Resolved this sprint (closed between @StartDate and today)
   b. Still open as of today
3. For open impediments older than 5 days, flag as "escalation candidate"
4. Write to Key Insights slide in deck.md:

   Impediments:
   - Cleared this sprint: [N]
   - Still open: [N] ([list titles of open items, one per line])
   - Escalation candidates (>5 days open): [titles, assigned to, age in days]

5. If no blocked items found, write: "No open impediments recorded in ADO."
```

---

## Agent 12: Backlog Readiness

**Updates:** `deck.md` — Next Sprint slide, Readiness section

```
Check that items planned for next sprint meet the Definition of Ready.

Definition of Ready checklist (adjust to your team's standards):
  - Has Acceptance Criteria (description field non-empty)
  - Has Story Points / Effort estimate (not 0 or null)
  - Is assigned to an area path and iteration
  - Is not blocked

WIQL — next sprint candidates (items in the backlog, not yet started):
SELECT [System.Id], [System.Title], [System.State],
       [Microsoft.VSTS.Scheduling.StoryPoints],
       [Microsoft.VSTS.Common.AcceptanceCriteria],
       [System.IterationPath]
FROM WorkItems
WHERE [System.WorkItemType] IN ('User Story', 'Feature', 'Request')
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] IN ('New', 'Active', 'Ready')
  AND [System.IterationPath] NOT UNDER '@CurrentIteration'

Steps:
1. Run the query
2. For each item, check each DoR criterion — mark pass/fail
3. Count: [N] of [total] items meet all DoR criteria
4. List items failing DoR with specific missing fields
5. Update the Next Sprint slide in deck.md:

   Backlog readiness:
   - [N] of [total] items ready for sprint planning
   - Not ready: [list titles + missing fields]

6. Prompt: "Do you want me to add a comment to the failing items in ADO? (y/n)"
   If yes, add a comment to each failing item listing the missing fields.
```

---

## Agent 13: Velocity Tracker

**Updates:** `deck.md` — Operations Overview slide, Velocity row

```
Calculate sprint velocity and 4-sprint rolling average.

WIQL — completed stories with points, last 4 sprints:
SELECT [System.Id], [System.IterationPath],
       [Microsoft.VSTS.Scheduling.StoryPoints],
       [Microsoft.VSTS.Common.ClosedDate]
FROM WorkItems
WHERE [System.WorkItemType] IN ('User Story', 'Task')
  AND [System.AreaPath] UNDER '@AreaPath'
  AND [System.State] IN ('Closed', 'Done')
  AND [Microsoft.VSTS.Common.ClosedDate] >= '@StartDate - 56 days'

Steps:
1. Run the WIQL query
2. Group by IterationPath (sprint), sum StoryPoints per sprint
3. Identify this sprint and the three before it
4. Calculate:
   - This sprint velocity: sum of points closed in @CurrentIteration
   - 4-sprint rolling average: mean of last 4 sprints
   - Delta vs average: this sprint - rolling average
5. Update the Operations Overview table in deck.md, adding a Velocity row:

   | Velocity (points) | [this sprint] | [rolling avg] |

6. Write a one-line trend note for the Key Insights slide:
   Velocity: [N] points ([+/-X] vs 4-sprint avg of [avg])
```
