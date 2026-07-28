# Example: BMAD Spec-First Build — Model-Serving Golden Path

**Goal:** Run a platform capability build through BMAD's agent pipeline (PRD → architecture → GitOps YAML → spec compliance) instead of starting from a blank YAML file.

Related blog post: [BMAD in Practice: Two Specs, One Method, Zero Blank YAML Files](https://www.polarpoint.io/blog/2026/07/28/bmad-in-practice-two-specs-one-method-zero-blank-yaml-files/)

## Problem

Golden paths make promises to other teams, but most get built YAML-first: the architecture decisions happen implicitly, one resource at a time, with no artifact forcing questions like "who gets paged when a model passes canary but fails the eval gate?" The decisions that were never made explicitly become the 2am incidents.

## Workflow

1. **PRD (Preston)**: two-sentence idea in, interrogated PRD out — users, success metrics, out-of-scope, constraints
2. **Architecture (Winston)**: PRD into decisions with reasons attached (KServe vs raw vLLM, Rollouts vs Flagger, Git-pinned registry refs)
3. **Implementation (Sam)**: decisions into GitOps YAML — ApplicationSet, InferenceService, eval-gate AnalysisTemplate
4. **Compliance (Quinn)**: generated YAML read against the PRD; drift flagged before merge
5. **Commit**: `docs/prd.md` and `docs/architecture.md` land in the repo next to the YAML they justify

## Inputs

- BMAD v6.8+ (`npx bmad-method@latest install`), agents: Preston, Winston, Sam, Quinn
- Model registry with evaluated, versioned artifacts
- Existing GitOps stack: ArgoCD, Argo Rollouts, Prometheus

## Outputs

- `docs/prd.md` — interrogated requirements with owned decisions
- `docs/architecture.md` — decisions with reasons
- `gitops/apps/model-serving-appset.yaml` — one Application per model per environment
- `models/<name>/envs/<env>/rollout-analysis.yaml` — eval-gated promotion
- Quinn compliance report — spec drift caught pre-merge

## PRD sections that do the work

| Section | What it forces |
|---------|----------------|
| **Success metrics** | Model deploys per week, publish-to-prod lead time, zero ungated changes — numbers, not "improve DX" |
| **Constraints** | Eval gate mandatory; golden dataset owner + refresh cadence; canary GPU budget; gate failure pages the *model owner* |
| **Out of scope** | Training pipelines, multi-region failover — the v1 boundary in writing |

## The eval gate

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: eval-gate
spec:
  metrics:
    - name: eval-score
      interval: 5m
      failureLimit: 1
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: avg(model_eval_score{model="support-summariser",track="canary"})
      successCondition: result[0] >= 0.87
```

## When to use this pattern

If the thing you're building makes promises to other teams — golden paths, self-service APIs, incident tooling — spec it. A one-file fix doesn't need a PRD. The threshold is promises, not size.
