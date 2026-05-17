# Sprint Review Agents — Jira

## Configuration

```yaml
project_key: "PLAT"           # Jira project key
board_id: 42                   # Jira board ID (from board URL)
sprint_duration_days: 14
tracker: jira
```

Custom field conventions assumed by these agents (adjust to your Jira instance):
- Request complexity: `customfield_10100` (values: Simple, Medium, Complex)
- Requesting team: `customfield_10101`
- Story points: `customfield_10016` (standard Jira story points field)

These values are substituted into every JQL query. Change them once here; all agents pick them up.

> **Note:** Custom field IDs vary by Jira instance. Run `GET /rest/api/3/field` to list all fields and find the correct IDs for your instance.

---

## Master Agent: Populate All Slides and Diagrams

```
You are coordinating a sprint review deck update.

Steps:
1. Calculate @StartDate as today minus 14 days (ISO 8601 format: YYYY-MM-DD)
2. Set @ProjectKey from the configuration block above
3. Ask the user: "Ready to query Jira and update the deck. Proceed? (y/n)"
4. If yes, run agents in this order:
   - Agent 1: Request Counts by Category
   - Agent 2: Resolution Time Trends
   - Agent 3: SLA Compliance
   - Agent 4: Request Complexity Distribution
   - Agent 5: Requestor Patterns
   - Agent 6: Request Metrics Summary (arithmetic — runs after 1–5)
   - Agent 7: Platform Development Summary (template only — no Jira query)
   - Agent 8: Key Insights (comparative — runs after 6)
   - Agent 9: Next Sprint Objectives (template only — prompts for input)
5. After all agents complete, report a summary of what was updated
6. Suggest running: make diagrams && make html
```

---

## Agent 1: Request Counts by Category

**Updates:** `diagrams/request-distribution.puml`

```
Query Jira for all Requests created in the last 14 days.

JQL:
project = "@ProjectKey"
  AND issuetype = Request
  AND created >= "@StartDate"
ORDER BY created DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=summary,labels,created,status

Steps:
1. Run the JQL query (paginate with maxResults=100 if needed)
2. Group results by label (first label = category)
   If no label, group under "Uncategorised"
3. Count issues per category
4. Update the bar data array in diagrams/request-distribution.puml:
   Replace each "Category" N line with the new count
5. Preserve all other lines in the file
```

---

## Agent 2: Resolution Time Trends

**Updates:** `diagrams/resolution-time-trends.puml`

```
Query Jira for resolved Requests and calculate daily average resolution time.

JQL:
project = "@ProjectKey"
  AND issuetype = Request
  AND status = Done
  AND created >= "@StartDate"
ORDER BY created DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=summary,created,resolutiondate

Steps:
1. Run the JQL query
2. For each issue, calculate resolution days = resolutiondate - created
3. Group by day (created date part), average resolution days per day
4. Update the line chart data points in diagrams/resolution-time-trends.puml
5. Format dates as DD/MM for the axis labels
```

---

## Agent 3: SLA Compliance

**Updates:** `deck.md` — "SLA Compliance" table in the Operations Overview slide

```
Query Jira for all Requests and check SLA thresholds.

SLA thresholds (adjust to match your team's targets):
  Simple requests: 2 business days
  Medium requests: 5 business days
  Complex requests: 10 business days

JQL:
project = "@ProjectKey"
  AND issuetype = Request
  AND created >= "@StartDate"
ORDER BY created DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=summary,created,resolutiondate,status,customfield_10100

Steps:
1. Run the JQL query
2. For each resolved issue, read customfield_10100 to determine complexity
3. Check if resolution time (resolutiondate - created) <= SLA threshold
4. Calculate: met_sla / total_resolved * 100 = compliance %
5. Update the SLA row in the Operations Overview table in deck.md
```

---

## Agent 4: Request Complexity Distribution

**Updates:** `diagrams/request-complexity.puml`

```
Query Jira for Requests and group by complexity field.

JQL:
project = "@ProjectKey"
  AND issuetype = Request
  AND created >= "@StartDate"
ORDER BY created DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=customfield_10100

Steps:
1. Run the JQL query
2. Count issues where customfield_10100 = Simple, Medium, Complex
3. Issues with null complexity: group under "Uncategorised"
4. Update the three bar values in diagrams/request-complexity.puml
```

---

## Agent 5: Requestor Patterns

**Updates:** `diagrams/requestor-patterns.puml`

```
Query Jira for Requests and group by requesting team.

JQL:
project = "@ProjectKey"
  AND issuetype = Request
  AND created >= "@StartDate"
ORDER BY created DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=customfield_10101

Steps:
1. Run the JQL query
2. Group by customfield_10101 (requesting team), count requests per team
3. Sort descending, take top 5
4. Update the bar data array in diagrams/requestor-patterns.puml with the top 5
5. If fewer than 5 teams, fill remaining bars with count 0
```

---

## Agent 6: Request Metrics Summary

**Updates:** `deck.md` — Operations Overview slide metrics table

```
This agent does arithmetic on the data already collected by Agents 1–5.
No Jira query needed — use the counts from previous agents.

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
This agent does not query Jira. It outputs a slide template and prompts the
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
This agent does not query Jira. It clears the previous sprint's objectives
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
2. Set @ProjectKey and @BoardId from the configuration block above
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

JQL — completed issues this sprint:
project = "@ProjectKey"
  AND sprint in openSprints()
  AND status in (Done, Resolved, Closed)
ORDER BY resolutiondate DESC

JQL — all committed issues this sprint (including incomplete):
project = "@ProjectKey"
  AND sprint in openSprints()
ORDER BY created ASC

API call:
GET /rest/agile/1.0/board/@BoardId/sprint?state=active
GET /rest/agile/1.0/sprint/<sprintId>/issue?jql=<encoded JQL>

Steps:
1. Fetch current active sprint ID from the board
2. Run both JQL queries scoped to that sprint
3. Calculate: completion rate = done / total * 100
4. Rate the sprint goal:
   - >= 80% done → "met"
   - 50–79% → "partially met"
   - < 50% → "not met"
5. Prompt: "What was the sprint goal this sprint?" — accept one sentence from user
6. Write to Key Insights slide in deck.md:
   Sprint goal: [status] — [user-provided goal sentence]
   Completion rate: [N]% ([done] of [total] issues)
```

---

## Agent 11: Impediment Summary

**Updates:** `deck.md` — Impediments section in Key Insights slide

```
Surface open blockers and impediments so they can be raised in the review.

JQL — blocked issues:
project = "@ProjectKey"
  AND status != Done
  AND (labels = blocked OR labels = impediment OR status = Blocked)
ORDER BY created ASC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=summary,created,assignee,labels,status

Steps:
1. Run the JQL query
2. Group results:
   a. Resolved this sprint (resolutiondate >= @StartDate)
   b. Still open as of today
3. For open impediments older than 5 days, flag as "escalation candidate"
4. Write to Key Insights slide in deck.md:

   Impediments:
   - Cleared this sprint: [N]
   - Still open: [N] ([list titles of open items, one per line])
   - Escalation candidates (>5 days open): [titles, assignee, age in days]

5. If no blocked issues found, write: "No open impediments recorded in Jira."
```

---

## Agent 12: Backlog Readiness

**Updates:** `deck.md` — Next Sprint slide, Readiness section

```
Check that issues planned for next sprint meet the Definition of Ready.

Definition of Ready checklist (adjust to your team's standards):
  - Has a description (non-empty)
  - Has story points (customfield_10016 not null and > 0)
  - Is assigned to a sprint (not in Backlog)
  - Is not blocked

JQL — next sprint candidates:
project = "@ProjectKey"
  AND sprint in futureSprints()
  AND issuetype in (Story, Task, Request)
ORDER BY priority DESC

API call:
GET /rest/api/3/search?jql=<encoded JQL>&fields=summary,description,customfield_10016,assignee,labels,sprint

Steps:
1. Run the JQL query
2. For each issue, check each DoR criterion — mark pass/fail
3. Count: [N] of [total] issues meet all DoR criteria
4. List issues failing DoR with the specific missing fields
5. Update the Next Sprint slide in deck.md:

   Backlog readiness:
   - [N] of [total] issues ready for sprint planning
   - Not ready: [list titles + missing fields]

6. Prompt: "Do you want me to add a comment to the failing issues in Jira? (y/n)"
   If yes, POST /rest/api/3/issue/<issueId>/comment for each failing issue.
```

---

## Agent 13: Velocity Tracker

**Updates:** `deck.md` — Operations Overview slide, Velocity row

```
Calculate sprint velocity and 4-sprint rolling average.

API calls:
GET /rest/agile/1.0/board/@BoardId/sprint?state=closed&maxResults=4
  → get last 4 closed sprint IDs

For each sprint:
GET /rest/agile/1.0/sprint/<sprintId>/issue?fields=customfield_10016,status
  → sum story points for Done issues

Steps:
1. Fetch the last 4 closed sprint IDs from the board
2. For each sprint, sum customfield_10016 (story points) for issues in status Done
3. Identify this sprint and the three before it
4. Calculate:
   - This sprint velocity: sum of points in current sprint
   - 4-sprint rolling average: mean of last 4 sprints
   - Delta vs average: this sprint - rolling average
5. Update the Operations Overview table in deck.md, adding a Velocity row:

   | Velocity (points) | [this sprint] | [rolling avg] |

6. Write a one-line trend note for the Key Insights slide:
   Velocity: [N] points ([+/-X] vs 4-sprint avg of [avg])

Note: If story points aren't used, substitute issue count as a proxy for
velocity — remove the customfield_10016 field and count issues instead.
```
