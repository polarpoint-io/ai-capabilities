# Example: External Secrets Operator + ArgoCD

**Goal:** Remove plaintext secrets from Git entirely — store values in your secret manager, commit only ExternalSecret manifests, let ESO pull and materialise secrets at deploy time.

Related blog post: [Why You Should Use External Secrets Operator with ArgoCD](/blog/2023/11/30/cloud-native-patterns-why-you-should-use-external-secrets-operator-with-argo-cd/)

## Problem

GitOps made deployments clean but secrets became the weak link. Teams either commit base64-encoded secrets (bad), maintain manual `kubectl create secret` steps outside the GitOps workflow (fragile), or invent bespoke workarounds that nobody else understands. ESO solves all three.

## Workflow

1. **Store**: put the secret value in your secret manager (AWS Secrets Manager, GCP Secret Manager, Vault, Azure Key Vault)
2. **Commit**: add an `ExternalSecret` manifest to Git — it contains only the reference path, no values
3. **Sync**: ArgoCD syncs the `ExternalSecret` manifest to the cluster as normal
4. **Materialise**: ESO reads the `ExternalSecret`, authenticates to the secret manager, creates a standard Kubernetes `Secret`
5. **Rotate**: update the value in your secret manager — ESO picks it up on the next refresh interval, no GitOps change required

## SecretStore (how to connect)

```yaml
# secretstore-aws.yaml — apply once per namespace or use ClusterSecretStore
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: eu-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

```yaml
# secretstore-vault.yaml — HashiCorp Vault alternative
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-secrets
  namespace: production
spec:
  provider:
    vault:
      server: https://vault.example.com
      path: secret
      version: v2
      auth:
        kubernetes:
          mountPath: kubernetes
          role: external-secrets
          serviceAccountRef:
            name: external-secrets-sa
```

## ExternalSecret (what to fetch)

```yaml
# externalsecret-database.yaml — this is what lives in Git
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: database-credentials      # name of the Kubernetes Secret to create
    creationPolicy: Owner
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: /production/database/credentials
        property: password
    - secretKey: DB_USERNAME
      remoteRef:
        key: /production/database/credentials
        property: username
    - secretKey: DB_HOST
      remoteRef:
        key: /production/database/credentials
        property: host
```

## Multi-environment pattern

Use a ClusterSecretStore per environment and reference by name convention:

```yaml
# production ExternalSecret
spec:
  secretStoreRef:
    name: aws-secrets-production
    kind: ClusterSecretStore

# staging ExternalSecret (same manifest structure, different store)
spec:
  secretStoreRef:
    name: aws-secrets-staging
    kind: ClusterSecretStore
```

The same ExternalSecret template works across environments — only the store reference changes, and that can be templated via Helm or Kustomize overlays.

## Scripts

```bash
# Install ESO via Helm
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace \
  --set installCRDs=true

# Validate an ExternalSecret is syncing correctly
kubectl get externalsecret database-credentials -n production -o wide

# Check ESO sync status (should show Ready=True)
kubectl describe externalsecret database-credentials -n production | grep -A5 Conditions

# List all ExternalSecrets and their sync status across cluster
kubectl get externalsecrets -A
```

## Environment variables required

```bash
# For AWS Secrets Manager
AWS_ACCESS_KEY_ID=<key>           # or use IRSA / pod identity
AWS_SECRET_ACCESS_KEY=<secret>
AWS_REGION=eu-west-2

# For Vault
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=<token>               # or use Kubernetes auth
```

## Inputs

- Secret values stored in AWS Secrets Manager / GCP Secret Manager / Vault / Azure Key Vault
- `SecretStore` or `ClusterSecretStore` manifests (created once per cluster/namespace)
- `ExternalSecret` manifests (one per secret, live in Git)

## Outputs

- Standard Kubernetes `Secret` objects created and maintained by ESO
- Auto-rotation: values updated in the cluster when the secret manager value changes (on `refreshInterval`)
- Policy reports via ArgoCD: ExternalSecret sync status visible as health checks

## Migration from raw Secrets

1. Identify all `Secret` manifests in Git that contain actual values (not ExternalSecrets)
2. Move the values to your secret manager under a structured path convention (`/<env>/<service>/<secret-name>`)
3. Replace the `Secret` manifest with an `ExternalSecret` pointing to the new path
4. Apply the `ExternalSecret` — ESO creates the Kubernetes Secret
5. Delete the old `Secret` manifest from Git and from the cluster

Migrate the most sensitive secrets first: database credentials, API keys, service account tokens. Work through the rest incrementally.
