#!/usr/bin/env python3
"""
validate-service.py — Validate a self-service GitOps service definition YAML.

Checks that a service definition file conforms to the schema expected by the
ArgoCD ApplicationSet matrix generator before it reaches the cluster.

Usage:
    python scripts/gitops/validate-service.py \
        --file teams/payments/services/payments-api.yaml

    # Validate all service definitions in a directory
    python scripts/gitops/validate-service.py \
        --dir teams/payments/services/

    # Strict mode — fail on warnings as well as errors
    python scripts/gitops/validate-service.py \
        --file teams/payments/services/payments-api.yaml \
        --strict

Exit codes:
    0 — valid (or valid with warnings in non-strict mode)
    1 — validation errors found
    2 — file not found or unreadable

Requires:
    pip install pyyaml
"""

import sys
import os
import argparse
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

# Valid values for constrained fields
VALID_TIERS = {"bronze", "silver", "gold"}
VALID_TYPES = {"api-service", "worker", "cron-job", "web-app", "library"}
VALID_ENVIRONMENTS = {"dev", "staging", "production"}
VALID_PROTOCOLS = {"http", "grpc", "tcp"}

# Required top-level keys
REQUIRED_KEYS = ["name", "team", "type", "tier", "environments"]

# Required keys within each environment block
REQUIRED_ENV_KEYS = ["replicaCount", "resources"]

# Required keys within resources
REQUIRED_RESOURCE_KEYS = ["requests", "limits"]
REQUIRED_RESOURCE_SUB_KEYS = ["cpu", "memory"]


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def __len__(self):
        return len(self.errors) + len(self.warnings)


def validate_resource_block(block: dict, path: str, result: ValidationResult):
    """Validate a resources.requests or resources.limits block."""
    for sub_key in REQUIRED_RESOURCE_SUB_KEYS:
        if sub_key not in block:
            result.error(f"{path}.{sub_key} is required")
        elif not isinstance(block[sub_key], str):
            result.error(f"{path}.{sub_key} must be a string (e.g. '100m', '256Mi')")


def validate_environment_block(env_name: str, env_block: dict, result: ValidationResult):
    """Validate a single environment block within spec.environments."""
    path = f"environments.{env_name}"

    for key in REQUIRED_ENV_KEYS:
        if key not in env_block:
            result.error(f"{path}.{key} is required")

    # Validate replicaCount
    if "replicaCount" in env_block:
        rc = env_block["replicaCount"]
        if not isinstance(rc, int) or rc < 0:
            result.error(f"{path}.replicaCount must be a non-negative integer")
        if rc == 0:
            result.warn(f"{path}.replicaCount is 0 — service will be scaled down in {env_name}")

    # Validate resources
    if "resources" in env_block:
        resources = env_block["resources"]
        for section in REQUIRED_RESOURCE_KEYS:
            if section not in resources:
                result.error(f"{path}.resources.{section} is required")
            else:
                validate_resource_block(resources[section], f"{path}.resources.{section}", result)

    # Validate image override if present
    if "image" in env_block:
        img = env_block["image"]
        if isinstance(img, dict):
            if "tag" in img and img["tag"] == "latest" and env_name == "production":
                result.error(f"{path}.image.tag: 'latest' is not allowed in production")
        elif isinstance(img, str) and ":latest" in img and env_name == "production":
            result.error(f"{path}.image: 'latest' tag is not allowed in production")

    # Check for HPA config consistency
    if "hpa" in env_block:
        hpa = env_block["hpa"]
        rc = env_block.get("replicaCount", 1)
        min_r = hpa.get("minReplicas", 1)
        max_r = hpa.get("maxReplicas", 1)

        if min_r > max_r:
            result.error(f"{path}.hpa.minReplicas ({min_r}) must be <= maxReplicas ({max_r})")
        if rc > max_r:
            result.warn(f"{path}.replicaCount ({rc}) exceeds hpa.maxReplicas ({max_r})")


def validate_service_definition(data: dict, filename: str) -> ValidationResult:
    """Run all validations against a parsed service definition dict."""
    result = ValidationResult()

    # --- Top-level required keys ---
    for key in REQUIRED_KEYS:
        if key not in data:
            result.error(f"Missing required field: '{key}'")

    # --- name ---
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name:
            result.error("'name' must be a non-empty string")
        elif not name.replace("-", "").isalnum():
            result.error(f"'name' must be alphanumeric with hyphens only, got: '{name}'")
        elif len(name) > 63:
            result.error(f"'name' must be <= 63 characters (DNS label limit), got: {len(name)}")

    # --- team ---
    if "team" in data:
        if not isinstance(data["team"], str) or not data["team"]:
            result.error("'team' must be a non-empty string")

    # --- type ---
    if "type" in data:
        svc_type = data["type"]
        if svc_type not in VALID_TYPES:
            result.error(f"'type' must be one of {sorted(VALID_TYPES)}, got: '{svc_type}'")

    # --- tier ---
    if "tier" in data:
        tier = data["tier"]
        if tier not in VALID_TIERS:
            result.error(f"'tier' must be one of {sorted(VALID_TIERS)}, got: '{tier}'")

    # --- owner ---
    if "owner" not in data:
        result.warn("'owner' is not set — recommend adding an owner email or Slack handle")
    elif "@" not in str(data.get("owner", "")):
        result.warn("'owner' should be an email address for clear escalation path")

    # --- environments ---
    if "environments" in data:
        envs = data["environments"]
        if not isinstance(envs, dict) or not envs:
            result.error("'environments' must be a non-empty mapping")
        else:
            # Warn if production is defined but staging is not
            if "production" in envs and "staging" not in envs:
                result.warn("'production' environment defined but 'staging' is missing — consider staging parity")

            for env_name, env_block in envs.items():
                if env_name not in VALID_ENVIRONMENTS:
                    result.warn(f"Non-standard environment name: '{env_name}' (expected one of {sorted(VALID_ENVIRONMENTS)})")
                if not isinstance(env_block, dict):
                    result.error(f"environments.{env_name} must be a mapping")
                    continue
                validate_environment_block(env_name, env_block, result)

    # --- alerts ---
    if data.get("tier") == "gold" and "alerts" not in data:
        result.warn("Gold-tier service has no 'alerts' block — SLO alerting is recommended")

    # --- port ---
    if "port" in data:
        port = data["port"]
        if not isinstance(port, int) or port < 1 or port > 65535:
            result.error(f"'port' must be an integer between 1 and 65535, got: {port}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def validate_file(path: Path, strict: bool) -> bool:
    """Validate a single service definition file. Returns True if valid."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: Cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"ERROR: YAML parse error in {path}:")
        print(f"  {e}")
        return False

    if not isinstance(data, dict):
        print(f"ERROR: {path}: top-level structure must be a YAML mapping")
        return False

    result = validate_service_definition(data, str(path))

    # Print results
    name = data.get("name", path.stem)
    print(f"\n{'─' * 60}")
    print(f"  {path.name}  →  service: {name!r}")
    print(f"{'─' * 60}")

    if result.errors:
        for err in result.errors:
            print(f"  ✗ ERROR   {err}")

    if result.warnings:
        for warn in result.warnings:
            print(f"  ⚠ WARNING {warn}")

    if result.is_valid and not result.warnings:
        print(f"  ✓ Valid")
    elif result.is_valid:
        print(f"  ✓ Valid (with {len(result.warnings)} warning(s))")

    if strict:
        return result.is_valid and len(result.warnings) == 0
    return result.is_valid


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate GitOps self-service service definition YAML files"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single service definition YAML file")
    group.add_argument("--dir", help="Directory containing service definition YAML files")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    return parser.parse_args()


def main():
    if not HAS_YAML:
        print("Error: 'pyyaml' package required. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    files: list[Path] = []

    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(2)
        files = [p]
    else:
        d = Path(args.dir)
        if not d.exists():
            print(f"Error: directory not found: {args.dir}", file=sys.stderr)
            sys.exit(2)
        files = sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml"))
        if not files:
            print(f"No YAML files found in {args.dir}")
            sys.exit(0)

    all_valid = True
    for f in files:
        valid = validate_file(f, strict=args.strict)
        if not valid:
            all_valid = False

    print(f"\n{'─' * 60}")
    if all_valid:
        print(f"  Result: ALL {len(files)} FILE(S) VALID")
        sys.exit(0)
    else:
        print(f"  Result: VALIDATION FAILED — fix errors above before merging")
        sys.exit(1)


if __name__ == "__main__":
    main()
