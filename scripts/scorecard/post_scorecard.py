"""
Post the monthly platform scorecard to Slack.

Usage:
    SLACK_WEBHOOK=<url> SCORECARD_FILE=/tmp/scorecard.md python post_scorecard.py

Reads the Markdown scorecard from SCORECARD_FILE and posts it to the Slack
webhook configured in SLACK_WEBHOOK. The message is formatted using Slack's
mrkdwn syntax so headers and tables render cleanly.

Optional env vars:
    SLACK_CHANNEL  — override the webhook's default channel (e.g. #platform-leads)
"""

import os
import re
import json
import requests
from datetime import datetime


def md_to_slack(text: str) -> str:
    """Convert a subset of Markdown to Slack mrkdwn."""
    # ## Heading → *Heading*
    text = re.sub(r"^## (.+)$", r"*\1*", text, flags=re.MULTILINE)
    # ### Heading → _Heading_
    text = re.sub(r"^### (.+)$", r"_\1_", text, flags=re.MULTILINE)
    # **bold** → *bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Markdown table rows → plain text (Slack doesn't render tables)
    # Keep the header separator rows stripped
    text = re.sub(r"^\|[-| :]+\|$", "", text, flags=re.MULTILINE)
    return text.strip()


def post_to_slack(scorecard_text: str) -> None:
    webhook_url = os.environ["SLACK_WEBHOOK"]
    month = datetime.now().strftime("%B %Y")

    slack_text = md_to_slack(scorecard_text)

    payload = {
        "text": f":bar_chart: *Platform Health Scorecard — {month}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Platform Health Scorecard — {month}",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": slack_text[:2900]},  # Slack block limit
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"Generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} · "
                            "Questions? → #platform-engineering"
                        ),
                    }
                ],
            },
        ],
    }

    # Optional channel override
    channel = os.environ.get("SLACK_CHANNEL")
    if channel:
        payload["channel"] = channel

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Scorecard posted to Slack (HTTP {resp.status_code})")


if __name__ == "__main__":
    scorecard_path = os.environ.get("SCORECARD_FILE", "/tmp/scorecard.md")
    with open(scorecard_path) as f:
        scorecard_text = f.read()

    post_to_slack(scorecard_text)
