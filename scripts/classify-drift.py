#!/usr/bin/env python3
"""
classify-drift.py — Classify a kubectl diff using AI to identify harmless vs risky drift.

Usage:
    python scripts/classify-drift.py <app-name> <diff-file>

    ANTHROPIC_API_KEY=<key> python scripts/classify-drift.py payments-api /tmp/drift-payments-api.diff

Output:
    JSON classification to stdout.
    Exit code 0 = classified successfully.
    Exit code 1 = error.

Verdicts:
    HARMLESS     — controller-managed fields, status updates, injected sidecars
    NEEDS_REVIEW — could be intentional or drift; worth a human look
    RISKY        — likely manual edit to spec fields; should be addressed
"""

import sys
import json
import os
import anthropic

CLASSIFIER_SYSTEM_PROMPT = """
You are a Kubernetes GitOps drift classifier. You receive the output of `argocd app diff`
or `kubectl diff` showing what differs between the Git desired state and the live cluster state.

Classify each changed resource with one of:

HARMLESS — Fields that are expected to differ because they are managed by controllers,
           the Kubernetes API server, or admission webhooks. Examples:
           - status.* fields (any status subresource)
           - metadata.resourceVersion, metadata.uid, metadata.creationTimestamp
           - metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
           - spec.nodeName, spec.serviceAccount (populated by scheduler)
           - Containers injected by Istio, Linkerd, or Datadog sidecars
           - metadata.annotations added by admission webhooks

NEEDS_REVIEW — Changes that could be intentional or could be drift. Should be looked at
               but do not indicate an emergency. Examples:
               - Helm-generated values that changed due to a chart update
               - Resource limits that differ slightly from values.yaml
               - Environment variables that may have been added via kubectl edit
               - Annotation or label changes that are not in the Git config

RISKY — Changes that strongly indicate a manual edit was applied directly to the cluster
         outside of the GitOps process. These should be resolved. Examples:
         - Manual changes to spec.containers[].resources (limits/requests)
         - Changes to spec.replicas outside of HPA management
         - Changes to securityContext settings
         - Changes to environment variables containing credentials or endpoints
         - Changes to volume mounts or secrets references
         - Network policy or RBAC changes not in Git

Output ONLY valid JSON in this format:
{
  "app_name": "<application name>",
  "resources": [
    {
      "name": "<resource name>",
      "kind": "<resource kind>",
      "namespace": "<namespace or cluster-scoped>",
      "verdict": "HARMLESS | NEEDS_REVIEW | RISKY",
      "confidence": 0.0-1.0,
      "reason": "<one sentence explaining the verdict>",
      "changed_fields": ["field1", "field2"]
    }
  ],
  "summary": {
    "harmless": 0,
    "needs_review": 0,
    "risky": 0,
    "action_required": true/false
  }
}

Be conservative: when uncertain, classify as NEEDS_REVIEW rather than HARMLESS.
"""


def classify_drift(app_name: str, diff_content: str) -> dict:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Application: {app_name}\n\nDiff output:\n```\n{diff_content}\n```",
            }
        ],
    )

    text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(text)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <app-name> <diff-file>", file=sys.stderr)
        sys.exit(1)

    app_name = sys.argv[1]
    diff_file = sys.argv[2]

    if not os.path.exists(diff_file):
        print(f"Error: diff file not found: {diff_file}", file=sys.stderr)
        sys.exit(1)

    with open(diff_file) as f:
        diff_content = f.read()

    if not diff_content.strip():
        print(f"Warning: diff file is empty: {diff_file}", file=sys.stderr)
        result = {
            "app_name": app_name,
            "resources": [],
            "summary": {
                "harmless": 0,
                "needs_review": 0,
                "risky": 0,
                "action_required": False,
            },
        }
        print(json.dumps(result, indent=2))
        return

    result = classify_drift(app_name, diff_content)
    print(json.dumps(result, indent=2))

    # Exit with non-zero if action is required (useful in CI)
    if result.get("summary", {}).get("action_required"):
        sys.exit(2)


if __name__ == "__main__":
    main()
