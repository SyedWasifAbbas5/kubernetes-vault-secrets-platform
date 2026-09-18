# Kubernetes Vault Secrets Platform

A production-style Kubernetes platform demonstrating **secure application secret management with HashiCorp Vault**, Kubernetes authentication, Vault Agent injection, RBAC, NetworkPolicy, container security, monitoring and CI security scanning.

The project is designed to run entirely in **GitHub Codespaces using kind**, so no paid cloud account is required.

---

## Architecture

```text
                    ┌─────────────────────┐
                    │     GitHub Repo     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   GitHub Actions    │
                    │                     │
                    │ • Python Tests      │
                    │ • Docker Build      │
                    │ • Trivy Scan        │
                    │ • K8s Validation    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Local Container    │
                    │     Registry        │
                    │      :5001          │
                    └──────────┬──────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │       kind Kubernetes Cluster  │
              │                                │
              │  ┌──────────────────────────┐  │
              │  │      Production NS       │  │
              │  │                          │  │
              │  │  ┌────────────────────┐  │  │
              │  │  │   Flask App        │  │  │
              │  │  │   Gunicorn         │  │  │
              │  │  │                    │  │  │
              │  │  │  /health           │  │  │
              │  │  │  /metrics          │  │  │
              │  │  │  /secret-status    │  │  │
              │  │  └─────────┬──────────┘  │  │
              │  │            │             │  │
              │  │      Vault Agent         │  │
              │  │      Injection           │  │
              │  └────────────┼─────────────┘  │
              │               │                │
              │               ▼                │
              │      ┌──────────────────┐      │
              │      │   HashiCorp Vault│      │
              │      │                  │      │
              │      │ Kubernetes Auth  │      │
              │      │ KV v2 Secrets    │      │
              │      │ Policies         │      │
              │      └──────────────────┘      │
              └────────────────────────────────┘
```

---

## What This Project Demonstrates

* Kubernetes application deployment
* HashiCorp Vault integration
* Kubernetes authentication with Vault
* KV v2 secret storage
* Vault policies and least-privilege access
* Vault Agent sidecar injection
* Automatic secret rendering
* Secret rotation without rebuilding the application image
* Kubernetes RBAC
* Kubernetes NetworkPolicy
* Container security hardening
* Non-root container execution
* Linux capability dropping
* Seccomp runtime profile
* Readiness and liveness probes
* Prometheus application metrics
* Docker image security scanning with Trivy
* Kubernetes manifest validation
* Automated Python testing
* GitHub Actions CI pipeline
* Local Kubernetes development with kind
* Local container registry integration

---

## Technology Stack

| Technology           | Purpose                             |
| -------------------- | ----------------------------------- |
| Kubernetes           | Container orchestration             |
| kind                 | Local Kubernetes cluster            |
| HashiCorp Vault      | Secret management                   |
| Vault Agent Injector | Secret injection                    |
| Docker               | Containerization                    |
| GitHub Actions       | CI automation                       |
| Trivy                | Container security scanning         |
| Kustomize            | Kubernetes configuration management |
| Python / Flask       | Demo application                    |
| Gunicorn             | Application server                  |
| Prometheus Client    | Application metrics                 |
| RBAC                 | Kubernetes access control           |
| NetworkPolicy        | Network isolation                   |

---

# Project Structure

```text
kubernetes-vault-secrets-platform/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app/
│   ├── __init__.py
│   ├── app.py
│   └── requirements.txt
│
├── tests/
│   └── test_app.py
│
├── k8s/
│   ├── base/
│   │   └── app.yaml
│   │
│   └── security/
│       ├── kustomization.yaml
│       ├── rbac.yaml
│       └── network-policy.yaml
│
├── Dockerfile
├── .dockerignore
└── kind-config.yaml
```

---

# Application

The project contains a lightweight Flask application running behind Gunicorn.

### Endpoints

| Endpoint                | Purpose                         |
| ----------------------- | ------------------------------- |
| `/`                     | Application information         |
| `/health`               | Kubernetes health check         |
| `/api/v1/secret-status` | Verifies Vault secret injection |
| `/metrics`              | Prometheus metrics              |

The application **does not expose the actual secret through its API**.

Instead, `/api/v1/secret-status` reports whether the secret was loaded and returns a short SHA-256 fingerprint.

Example:

```json
{
  "fingerprint": "fc40a0ecfa2f",
  "secret_loaded": true,
  "secret_source": "hashicorp-vault"
}
```

---

# HashiCorp Vault Integration

Vault stores application secrets using **KV version 2**.

Example secret structure:

```text
secret/
└── production/
    └── app
        ├── API_KEY
        └── DATABASE_URL
```

The Kubernetes application authenticates with Vault using the Kubernetes authentication method.

The application does not require a Vault root token.

Instead, its Kubernetes service account is mapped to a dedicated Vault role:

```text
vault-app
     │
     ▼
Vault Kubernetes Auth
     │
     ▼
production-app role
     │
     ▼
production-app policy
     │
     ▼
secret/data/production/app
```

---

# Vault Policy

The application is granted read-only access to its required secret path.

```hcl
path "secret/data/production/app" {
  capabilities = ["read"]
}
```

This follows the principle of **least privilege**.

The application cannot use this policy to access unrelated Vault paths.

---

# Vault Agent Injection

The Kubernetes deployment uses Vault Agent Injector annotations.

Example:

```yaml
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: "production-app"
vault.hashicorp.com/agent-inject-secret-app-secret: "secret/data/production/app"
```

Vault Agent authenticates using the application's Kubernetes service account and writes the secret to:

```text
/vault/secrets/app-secret
```

The application reads the secret from this mounted file rather than storing the secret inside the Docker image or Kubernetes Deployment manifest.

---

# Secret Rotation

One of the main demonstrations is secret rotation.

The application initially receives a secret from Vault.

The secret can then be changed in Vault without rebuilding the Docker image.

For example:

```bash
vault kv put secret/production/app \
  API_KEY="new-api-key" \
  DATABASE_URL="postgresql://demo-user:demo-password@database:5432/appdb"
```

Vault Agent detects the updated KV v2 secret and refreshes the rendered secret file.

The application can therefore consume the rotated value without embedding secrets in the container image.

---

# Kubernetes Security

## RBAC

The application runs using a dedicated Kubernetes service account:

```text
vault-app
```

The application namespace contains a restricted role with no Kubernetes API permissions.

This prevents the application from automatically receiving unnecessary Kubernetes API access.

---

## NetworkPolicy

Network traffic for the application is restricted using Kubernetes NetworkPolicy.

The policy controls:

* Ingress traffic
* DNS access
* HTTPS traffic
* HTTP traffic

This demonstrates basic workload network isolation rather than leaving every pod unrestricted.

---

# Container Security

The application container is hardened with Kubernetes security settings including:

```yaml
allowPrivilegeEscalation: false
runAsNonRoot: true
runAsUser: 1000
```

Linux capabilities are dropped:

```yaml
capabilities:
  drop:
    - ALL
```

The container also uses:

```yaml
seccompProfile:
  type: RuntimeDefault
```

The Docker image itself runs as a non-root user.

---

# Health Checks

Kubernetes uses the application's `/health` endpoint for readiness and liveness checks.

### Readiness

```text
/health
```

### Liveness

```text
/health
```

This allows Kubernetes to determine whether the application is ready to receive traffic and whether the container should be restarted.

---

# Monitoring

The application exposes Prometheus-compatible metrics at:

```text
/metrics
```

A request counter is included:

```text
vault_platform_requests_total
```

Prometheus scrape annotations are configured on the application pods.

This provides a simple foundation for integrating the workload with a Prometheus/Grafana monitoring stack.

---

# CI/CD Pipeline

GitHub Actions automatically performs several validation stages.

```text
Push / Pull Request
        │
        ▼
 Python Tests
        │
        ▼
 Docker Build
        │
        ▼
 Trivy Security Scan
        │
        ▼
 Kubernetes Manifest Validation
```

The workflow includes:

### 1. Python Tests

Runs the application's automated tests with `pytest`.

### 2. Docker Build

Builds the application container to verify that the Dockerfile and application dependencies are valid.

### 3. Trivy Security Scan

Scans the container image for known security vulnerabilities.

The pipeline is configured to fail on unfixed/high-severity findings according to the configured Trivy policy.

### 4. Kubernetes Validation

Kubernetes security manifests are validated as part of CI.

---

# Running Locally

The complete environment can be run using GitHub Codespaces and kind.

## Prerequisites

Install or have available:

* Docker
* kubectl
* kind
* Git
* GitHub Codespaces

No AWS account is required.

---

## Create the Cluster

```bash
kind create cluster \
  --name vault-platform \
  --config kind-config.yaml
```

Verify:

```bash
kubectl get nodes
```

Expected:

```text
vault-platform-control-plane   Ready
```

---

# Local Container Registry

The project uses a local registry so that kind can pull locally built images.

Example:

```text
localhost:5001
```

Build an image:

```bash
docker build \
  -t localhost:5001/vault-platform-app:1.4.0 .
```

Push it:

```bash
docker push localhost:5001/vault-platform-app:1.4.0
```

---

# Deploying the Application

Apply the base application:

```bash
kubectl apply -f k8s/base/app.yaml
```

Apply security configuration:

```bash
kubectl apply -k k8s/security
```

Check the deployment:

```bash
kubectl get pods -n production
```

Expected:

```text
vault-platform-app-xxxxx   2/2   Running
vault-platform-app-yyyyy   2/2   Running
```

Each application pod contains:

```text
app
vault-agent
```

---

# Verifying Vault Secret Injection

Check the injected secret file:

```bash
kubectl exec -n production <pod-name> -c app -- \
  python -c "from pathlib import Path; print(Path('/vault/secrets/app-secret').read_text())"
```

The secret is rendered by Vault Agent into the pod filesystem.

For normal application access, the application uses the secret internally rather than exposing its value through an API.

---

# Verify the Application

Port-forward the application:

```bash
kubectl port-forward \
  -n production \
  service/vault-platform-app \
  8080:80
```

Then test:

```bash
curl http://localhost:8080/health
```

Example response:

```json
{
  "status": "healthy"
}
```

Test Vault integration:

```bash
curl http://localhost:8080/api/v1/secret-status
```

Example:

```json
{
  "fingerprint": "fc40a0ecfa2f",
  "secret_loaded": true,
  "secret_source": "hashicorp-vault"
}
```

---

# Security Validation

Check the application service account:

```bash
kubectl get serviceaccount vault-app -n production
```

Check RBAC:

```bash
kubectl get role,rolebinding -n production
```

Check NetworkPolicy:

```bash
kubectl get networkpolicy -n production
```

Check container security:

```bash
kubectl get pod -n production \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
```

---

# Testing

Run application tests locally:

```bash
PYTHONPATH=. pytest -v
```

The tests verify the basic application endpoints.

Example:

```text
2 passed
```

---

# Security Considerations

This repository intentionally avoids committing real credentials.

Demo credentials used during local Vault development should be treated as disposable.

Do not commit:

* Production API keys
* Cloud credentials
* Database passwords
* Vault root tokens
* Private certificates
* Real `.env` files

For a real production deployment, Vault should run in a properly secured HA configuration with persistent storage, TLS, controlled authentication, backup/recovery procedures, and appropriate operational access controls.

---

# Environment

This project is designed as a **local production-style Kubernetes demonstration**.

The environment uses:

```text
GitHub Codespaces
        │
        ▼
Docker
        │
        ▼
kind Kubernetes
        │
        ├── production namespace
        │
        └── vault namespace
```

It does not claim to be a production AWS/EKS deployment.

The same concepts can be transferred to managed Kubernetes platforms such as EKS, AKS, or GKE with environment-specific changes.

---

# Key DevOps Concepts Demonstrated

This project brings together several real-world DevOps practices:

```text
Containerization
      +
CI/CD
      +
Security Scanning
      +
Kubernetes
      +
RBAC
      +
NetworkPolicy
      +
HashiCorp Vault
      +
Kubernetes Authentication
      +
Secret Injection
      +
Secret Rotation
      +
Health Checks
      +
Prometheus Metrics
```

The main objective is to demonstrate how an application can consume secrets securely without placing credentials directly inside source code, Docker images or Kubernetes manifests.

---

# Future Improvements

Possible extensions include:

* TLS-enabled Vault
* Vault HA deployment
* External Secrets Operator
* Ingress
* Prometheus deployment
* Grafana dashboards
* Alerting
* GitHub Actions image publishing
* Image signing
* SBOM generation
* Kubernetes policy enforcement
* Deployment promotion between environments

---

## License

MIT License.
