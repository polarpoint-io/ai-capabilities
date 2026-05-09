#!/usr/bin/env python3
"""
summarise-violations.py — Summarise Kyverno PolicyReport violations across the cluster.

Reads PolicyReport resources (per-namespace) and ClusterPolicyReport resources
via kubectl and produces a human-readable summary with violation counts by policy,
severity, and namespace. Useful for reviewing violations before switching a
policy from Audit to Enforce mode.

Usage:
    # Summarise all violations across the cluster
    python scripts/kyverno/summarise-violations.py

    # Filter to a specific namespace
    python scripts/kyverno/summarise-violations.py --namespace payments

    # Filter to a specific policy
    python scripts/kyverno/summarise-violations.py --policy require-resource-limits

    # Output as JSON for CI or further processing
    python scripts/kyverno/summarise-violations.py --output json

    # Show only failures (skip pass/skip/warn entries)
    python scripts/kyverno/summarise-violations.py --failures-only

    # Exit with code 1 if any violations found (useful in CI)
    python scripts/kyverno/summarise-violations.py --exit-on-violations

Environment variables:
    KUBECONFIG          Standard kubeconfig path
    KYVERNO_NAMESPACE   Kyverno namespace (default: kyverno)

Requires:
    kubectl in PATH
    python 3.9+
"""

import sys
import os
import json
import subprocess
import argparse
from collections import defaultdict
from typing import Optional


# ---------------------------------------------------------------------------
# kubectl helpers
# ---------------------------------------------------------------------------

def kubectl_get_json(resource: str, namespace: Optional[str] = None) -> list[dict]:
    """Run kubectl get <resource> -o json and return the items list."""
    cmd = ["kubectl", "get", resource, "-o", "json"]
    if namespace:
        cmd += ["-n", namespace]
    else:
        cmd += ["-A"]  # all namespaces for namespaced resources

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print("ERROR: kubectl not found in PATH.", file=sys.stderr)
        print("Install kubectl: https://kubernetes.io/docs/tasks/tools/", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"ERROR: kubectl timed out fetching {resource}", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "No resources found" in stderr or result.returncode == 1:
            return []
        if "the server doesn't have a resource type" in stderr:
            # Kyverno CRD not installed
            return []
        print(f"WARNING: kubectl error for {resource}: {stderr}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        print(f"WARNING: Could not parse kubectl output for {resource}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Report parsing
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "": 5}
RESULT_COLORS = {
    "fail":  "✗",
    "pass":  "✓",
    "warn":  "⚠",
    "skip":  "○",
    "error": "!",
}


def parse_policy_reports(
    namespace_filter: Optional[str],
    policy_filter: Optional[str],
    failures_only: bool,
) -> list[dict]:
    """
    Fetch and parse PolicyReport and ClusterPolicyReport resources.
    Returns a flat list of result entries with added metadata.
    """
    entries = []

    # Namespaced policy reports
    ns_reports = kubectl_get_json("policyreport", namespace=namespace_filter)
    for report in ns_reports:
        ns = report.get("metadata", {}).get("namespace", "unknown")
        report_name = report.get("metadata", {}).get("name", "unknown")
        for result in report.get("results", []):
            if failures_only and result.get("result") not in ("fail", "warn", "error"):
                continue
            if policy_filter and result.get("policy") != policy_filter:
                continue
            entries.append({
                "scope": "namespace",
                "namespace": ns,
                "report": report_name,
                "policy": result.get("policy", ""),
                "rule": result.get("rule", ""),
                "result": result.get("result", ""),
                "severity": result.get("severity", "").lower(),
                "message": result.get("message", ""),
                "resources": result.get("resources", []),
            })

    # Cluster-scoped policy reports (not namespace-filtered)
    if not namespace_filter:
        cluster_reports = kubectl_get_json("clusterpolicyreport")
        for report in cluster_reports:
            report_name = report.get("metadata", {}).get("name", "unknown")
            for result in report.get("results", []):
                if failures_only and result.get("result") not in ("fail", "warn", "error"):
                    continue
                if policy_filter and result.get("policy") != policy_filter:
                    continue
                entries.append({
                    "scope": "cluster",
                    "namespace": "(cluster)",
                    "report": report_name,
                    "policy": result.get("policy", ""),
                    "rule": result.get("rule", ""),
                    "result": result.get("result", ""),
                    "severity": result.get("severity", "").lower(),
                    "message": result.get("message", ""),
                    "resources": result.get("resources", []),
                })

    return entries


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarise_text(entries: list[dict], failures_only: bool):
    """Print a human-readable summary to stdout."""
    if not entries:
        print("\n  No violations found." if failures_only else "\n  No policy report entries found.")
        return

    # Group by result type
    by_result: dict[str, int] = defaultdict(int)
    by_policy: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_namespace: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)

    for e in entries:
        by_result[e["result"]] += 1
        by_policy[e["policy"]][e["result"]] += 1
        by_namespace[e["namespace"]] += 1
        if e["severity"]:
            by_severity[e["severity"]] += 1

    total = len(entries)
    fail_count = by_result.get("fail", 0) + by_result.get("error", 0)

    print(f"\n{'═' * 65}")
    print(f"  Kyverno Policy Violation Summary")
    print(f"{'═' * 65}")
    print(f"  Total entries:  {total}")
    print(f"  Failures:       {fail_count}")
    for result, count in sorted(by_result.items()):
        icon = RESULT_COLORS.get(result, "?")
        print(f"    {icon} {result:<10} {count}")

    # Severity breakdown (only if we have severity data)
    if by_severity:
        print(f"\n  By Severity:")
        for sev in sorted(by_severity.keys(), key=lambda s: SEVERITY_ORDER.get(s, 99)):
            print(f"    {sev:<12} {by_severity[sev]}")

    # Per-policy breakdown
    print(f"\n  By Policy:")
    sorted_policies = sorted(
        by_policy.items(),
        key=lambda x: x[1].get("fail", 0) + x[1].get("error", 0),
        reverse=True,
    )
    for policy, counts in sorted_policies:
        fail_n = counts.get("fail", 0) + counts.get("error", 0)
        warn_n = counts.get("warn", 0)
        pass_n = counts.get("pass", 0)
        parts = []
        if fail_n: parts.append(f"✗{fail_n} fail")
        if warn_n: parts.append(f"⚠{warn_n} warn")
        if pass_n: parts.append(f"✓{pass_n} pass")
        print(f"    {policy:<45} {', '.join(parts)}")

    # Per-namespace breakdown
    if len(by_namespace) > 1:
        print(f"\n  By Namespace (failures only):")
        sorted_ns = sorted(by_namespace.items(), key=lambda x: x[1], reverse=True)
        for ns, count in sorted_ns[:20]:  # top 20
            print(f"    {ns:<40} {count}")
        if len(sorted_ns) > 20:
            print(f"    ... and {len(sorted_ns) - 20} more namespaces")

    # Detail: show individual fail entries (up to 25)
    fail_entries = [e for e in entries if e["result"] in ("fail", "error")]
    if fail_entries:
        print(f"\n  Failure Detail (showing up to 25 of {len(fail_entries)}):")
        print(f"  {'─' * 63}")
        for e in fail_entries[:25]:
            resources = e.get("resources", [])
            res_str = ""
            if resources:
                r = resources[0]
                res_str = f" → {r.get('kind', '')}/{r.get('name', '')}"

            ns_str = f"[{e['namespace']}]" if e["namespace"] else ""
            sev_str = f" ({e['severity']})" if e["severity"] else ""
            print(f"  {ns_str:<20} {e['policy']}/{e['rule']}{sev_str}")
            print(f"  {'':20} {e['message'][:80]}{res_str}")
            print()

    print(f"{'═' * 65}")
    if fail_count > 0:
        print(f"  ⚠  {fail_count} failure(s) require attention before enforcing policies.")
    else:
        print(f"  ✓  No failures — cluster is policy-compliant.")
    print(f"{'═' * 65}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarise Kyverno policy violations across the cluster"
    )
    parser.add_argument("--namespace",         help="Filter to a specific namespace")
    parser.add_argument("--policy",            help="Filter to a specific policy name")
    parser.add_argument("--output",            choices=["text", "json"], default="text")
    parser.add_argument("--failures-only",     action="store_true", help="Only show fail/warn/error entries")
    parser.add_argument("--exit-on-violations",action="store_true", help="Exit with code 1 if any failures found")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Fetching policy reports from cluster...", end="", flush=True)
    entries = parse_policy_reports(
        namespace_filter=args.namespace,
        policy_filter=args.policy,
        failures_only=args.failures_only,
    )
    print(f" {len(entries)} entries found.")

    if args.output == "json":
        print(json.dumps(entries, indent=2))
    else:
        summarise_text(entries, failures_only=args.failures_only)

    if args.exit_on_violations:
        fail_count = sum(1 for e in entries if e["result"] in ("fail", "error"))
        if fail_count > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
