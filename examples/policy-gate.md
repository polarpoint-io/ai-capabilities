# Example: Policy Gate for Agent Changes

**Goal:** Validate AI-proposed infrastructure changes against OPA/Kyverno policies before a human reviews the PR.

Related blog post: [Policy as Code + Agents: Guardrails That Actually Hold](/blog/2026/04/08/policy-as-code-agents-guardrails-that-actually-hold/)

## Problem

Agents optimise for "make it work." Without a policy gate, an agent may propose a Kubernetes manifest without resource limits, a Terraform change that opens a database to the public internet, or a network policy that is too broad. Policy validation in CI catches these before a human reviewer ever sees them.

## Workflow

1. **Agent generates** a manifest, Terraform plan, or config change on a branch
2. **CI triggers** the policy gate on PR open
3. **Kyverno** validates Kubernetes manifests against cluster policies
4. **OPA/Conftest** validates Terraform plans against security policies
5. **Results posted** as a PR comment — pass, violations, or dismissed
6. **Agent self-corrects** if violations are found (using policy failure as feedback)

## Kyverno policies (Kubernetes)

Key policies to start with:

| Policy | What it enforces |
|--------|-----------------|
| `require-resource-limits` | All containers must have CPU and memory limits |
| `restrict-ingress-cidr` | No ingress from 0.0.0.0/0 or ::/0 |
| `require-labels` | All workloads must have `service` and `team` labels |
| `no-privileged-containers` | `securityContext.privileged` must be false |
| `require-readiness-probe` | All containers must define a readiness probe |

## OPA policies (Terraform)

| Policy | What it enforces |
|--------|-----------------|
| `security-groups` | No inbound rules from 0.0.0.0/0 |
| `rds-public` | `publicly_accessible` must be false |
| `s3-public` | S3 buckets must not be public |
| `encryption` | Storage resources must have encryption enabled |

## Self-correction loop

The agent can self-correct before opening a PR:

```python
# Pseudo-code: agent + policy validation loop
for attempt in range(3):
    manifest = generate_manifest(requirement)
    violations = run_kyverno(manifest, policies)
    
    if not violations:
        break
    
    # Feed violations back as context
    requirement = f"{original_requirement}\n\nPlease fix these policy violations:\n{violations}"
```

If the agent cannot produce a compliant manifest after 3 attempts, it opens a draft PR with the violations listed for human resolution.

## Scripts

```bash
# Run Kyverno against local manifests
kyverno apply kyverno/policies/ --resource k8s/

# Run OPA against Terraform plan
terraform plan -out=tfplan && terraform show -json tfplan > tfplan.json
conftest test tfplan.json --policy policies/terraform/

# Run both in sequence
bash scripts/policy-check.sh
```

## Agent prompts

- **Generator**: produce Kubernetes or Terraform code for the given requirement
- **Validator**: run policy checks and parse violations into structured feedback
- **Corrector**: receive policy violations as feedback, produce corrected output
- **Reporter**: post a concise policy check summary on the PR

## Files

```
kyverno/policies/
  require-resource-limits.yaml
  restrict-ingress-cidr.yaml
  require-labels.yaml
  no-privileged-containers.yaml

policies/terraform/
  security-groups.rego
  rds-public.rego
  s3-public.rego
  encryption.rego

scripts/
  policy-check.sh
```
