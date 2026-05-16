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
