"""
Generate a narrative platform health scorecard using Claude.

Usage:
    ANTHROPIC_API_KEY=<key> SCORECARD_DATA=/tmp/scorecard-data.json \
        python generate_scorecard.py

Reads current + previous month data from SCORECARD_DATA, passes it to Claude
claude-opus-4-6, and writes the Markdown scorecard to /tmp/scorecard.md
(override with SCORECARD_FILE env var).
"""

import json
import os
from datetime import datetime

import anthropic


client = anthropic.Anthropic()


def generate_scorecard(current: dict, previous: dict) -> str:
    """Generate a narrative scorecard with trend commentary."""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system="""You are a platform engineering analyst. Generate a monthly platform health scorecard.

Format:
## Platform Health: [Month Year]

**Overall trend:** [Improving / Stable / Declining] — [one sentence why]

### Metrics

| Metric | This Month | Last Month | Trend |
|--------|-----------|-----------|-------|
[table rows]

### What improved
[2-3 bullet points — specific, factual, with numbers]

### What needs attention
[2-3 bullet points — specific, factual, with a suggested action for each]

### Context
[1 paragraph — any relevant context that explains the numbers]

Rules:
- Use ↑ ↓ → for trend arrows (↑ = improved, ↓ = worsened, → = stable)
- Be specific: "Lead time decreased from 8.2 to 5.4 hours" not "lead time improved"
- Only flag changes >10% as meaningful movement
- Keep it under 300 words total — this is an executive summary, not a report
- Write for a technical leader who doesn't live in Grafana""",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Current month: {json.dumps(current, indent=2)}\n\n"
                    f"Previous month: {json.dumps(previous, indent=2)}"
                ),
            }
        ],
    )

    return response.content[0].text


def format_scorecard_email(narrative: str) -> str:
    """Wrap the narrative in an email-friendly format."""
    return (
        f"Subject: Platform Health Scorecard — {datetime.now().strftime('%B %Y')}\n\n"
        f"{narrative}\n\n"
        f"---\n"
        f"Data collected automatically on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}.\n"
        f"Questions? Reach the platform team in #platform-engineering.\n"
    )


if __name__ == "__main__":
    data_path = os.environ.get("SCORECARD_DATA", "/tmp/scorecard-data.json")
    with open(data_path) as f:
        data = json.load(f)

    narrative = generate_scorecard(data["current"], data["previous"])

    scorecard_path = os.environ.get("SCORECARD_FILE", "/tmp/scorecard.md")
    with open(scorecard_path, "w") as f:
        f.write(narrative)

    print(f"Scorecard written to {scorecard_path}")
    print(narrative)
