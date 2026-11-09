# Secure Flask App

![CI](https://github.com/MuskanSayyedCySec/secure-flask-app/actions/workflows/ci.yml/badge.svg)

A small Python web app taken from an insecure container to a hardened Kubernetes deployment, with a DevSecOps pipeline that tests and scans every change and blocks anything insecure from reaching the main branch.

Week 1 hardened the container. Week 2 automated every check in GitHub Actions and locked the main branch behind them. Week 3 deployed the app to Kubernetes with Pod Security, network rules and access rules.

## Container Results

Scanned with Trivy 0.76.1 on 25 October 2026. Vulnerability counts change as databases update.

| Measure                        | Insecure     | Hardened              |
|--------------------------------|--------------|-----------------------|
| Image size on disk             | 1.66 GB      | 212 MB (87% smaller)  |
| Known vulnerabilities          | 3,552        | 164 (95% fewer)       |
| Critical vulnerabilities       | 16           | 0                     |
| High vulnerabilities           | 441          | 44 (90% fewer)        |
| Python package vulnerabilities | 7            | 0                     |
| Dockerfile misconfigurations   | 3            | 0                     |
| Linux capabilities             | 14           | 0                     |
| Runs as                        | root (UID 0) | appuser (UID 10001)   |
| Secrets in image               | 1            | 0                     |

## Pipeline

Every push to main and every pull request runs three jobs in GitHub Actions. Main is locked by a ruleset with no bypass list, so nothing merges unless all three pass.

| Job                   | Checks                                                                                              | Blocks the merge when                                         |
|-----------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| Run tests             | 12 pytest tests, Bandit code scan, pip-audit dependency scan                                        | A test fails, risky code is found, or a package is vulnerable |
| Scan for secrets      | Gitleaks over the full Git history                                                                  | Any secret is found                                           |
| Build and check image | Docker build, non root, no pip, no test tools, Trivy image scan, Trivy scan of Dockerfile and Kubernetes files | Any image check fails, a fixable high or critical vulnerability, or a serious configuration problem |

| Pipeline test                                    | Result                                                      |
|--------------------------------------------------|-------------------------------------------------------------|
| Reintroduced a validation bug                    | Caught in 10 seconds, build skipped                         |
| Committed a fake API key                         | Caught by both Bandit and Gitleaks                          |
| Merged with failing checks, and as administrator | Both refused                                                |
| Pushed directly to main                          | Rejected                                                    |
| Two zlib vulnerabilities became fixable          | Blocked the next pull request until the image was patched   |

## Kubernetes Results

Deployed to a local kind cluster in Docker Desktop, Kubernetes 1.36.1.

| Control                | Setting                                                                                 | Proof                                                              |
|------------------------|-----------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Pod Security           | Namespace enforces the restricted level                                                 | An unhardened pod was refused for breaking 4 rules                 |
| Hardened pods          | Non root, no privilege escalation, all capabilities dropped, seccomp, read only file system | Live pod shows UID 10001, writes fail, capability set is all zeros |
| Secret handling        | Secret key created by command, never written to a file                                  | Not present anywhere in the repository                             |
| Availability           | 2 copies, readiness and liveness probes on /health, CPU and memory limits               | Rolling updates completed with no downtime                         |
| Network segmentation (zero trust) | Default deny on incoming traffic, only labelled pods may reach the app on port 8080 | Labelled pod connected, unlabelled pod timed out                   |
| Access control (least privilege) | Read only auditor role with no access to Secrets                            | 4 of 4 permission checks as designed, a real Secrets read refused  |
| Minimal access for the app | No Kubernetes API token mounted in the app pods                                     | Set in the deployment                                              |
| Image integrity        | Image copied into the node and checked by hash                                          | Hash inside the node matched the built image                       |

## Principles Applied

| Principle                   | Where                                                                                       |
|-----------------------------|---------------------------------------------------------------------------------------------|
| Least privilege             | Non root container, dropped capabilities, read only pipeline token, auditor role, no API token for the app |
| Zero trust and segmentation | Default deny network policy with one labelled exception                                     |
| Defence in depth            | Image hardening, Pod Security, pod settings and network rules each protect the app separately |
| Secure by default           | The namespace refuses unsafe pods instead of relying on people to remember the rules       |
| Immutability                | Read only file system, app code owned by root                                               |
| Shift left                  | Every change is tested and scanned before it reaches main                                   |
| Failing securely            | Any failed check stops the merge, and the build waits for tests and secret scanning        |
| Separation of duties        | Main is locked behind pull requests and required checks                                     |
| Integrity                   | Actions pinned to commit codes, tools and images verified by hash                          |

## Standards

CIS Docker Benchmark and Kubernetes Pod Security Standards (restricted level) for container and pod settings.

NIST SSDF practices for automated testing, dependency and secret scanning, and protecting the build pipeline.

OWASP Top 10 risks for injection, including cross site scripting, and security misconfiguration.

## Key Findings

**Test tools slipped into the image without any scanner noticing.** pytest and four helper packages got into the image during Week 2 through `requirements.txt`. Bandit, pip-audit, Gitleaks and Trivy all passed, because none of those packages were vulnerable. It was found by reading the scan output. They were removed, and a pipeline check now fails the build if test tools reach the image.

**Scan results go out of date.** The same image went from 164 to 186 known vulnerabilities in 12 days with no code change. Later, two zlib vulnerabilities became fixable, and the pipeline blocked the next pull request until Debian's security update was applied in the build.

**Built in standards are a minimum.** The restricted Pod Security level does not require a read only file system, so it was added separately.

**Scanners make mistakes in both directions.** A public Python signing key was flagged as a secret six times and allowed with a documented exception, while a fake secret made of readable words was not flagged at all.

## Documented Exceptions

| Exception                                       | Reason                                                                  |
|-------------------------------------------------|-------------------------------------------------------------------------|
| Public GPG key allowed in `.gitleaks.toml`      | It is the Python release signing key fingerprint, public by design      |
| Tests folder excluded from Bandit               | Tests use assert and a fixed subprocess call by design, and never ship  |
| `Dockerfile.insecure` skipped by Trivy          | Intentionally insecure, kept only for the before and after comparison   |
| Unfixed vulnerabilities reported, not blocked   | No fix exists yet, so blocking would stop every build with no way forward |

## Residual Risk

The pipeline scans the Kubernetes files but does not deploy them. GitHub's runners cannot reach the local cluster, so deployment is manual.

Kubernetes Secrets are encoded, not encrypted, in this local cluster. The auditor role shows how access to them is limited.

The network policy controls incoming traffic only. Outgoing traffic is not restricted.

Installing Debian updates during the build means two builds can contain slightly different package versions.

Pull requests need zero human approvals while working alone. A team should require at least one reviewer.

## Tech Stack

Python 3.13, Flask, Gunicorn, Docker, Docker Compose, Kubernetes, kind, kubectl, GitHub Actions, pytest, Bandit, pip-audit, Gitleaks, Trivy, Git

## How to Run

You need Docker Desktop.

**With Docker Compose**

```bash
git clone https://github.com/MuskanSayyedCySec/secure-flask-app.git
cd secure-flask-app
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build
curl -i http://127.0.0.1:8080/health
```

**On Kubernetes**, with a kind cluster created in Docker Desktop

```bash
docker build -t flask-app:hardened .
docker save flask-app:hardened | docker exec -i desktop-control-plane ctr -n k8s.io images import -
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic flask-secret -n secure-flask --from-literal=SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/network-policy.yaml -f k8s/rbac.yaml
kubectl port-forward -n secure-flask deployment/flask-app 8080:8080
```

**Tests and scanners locally**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
bandit -r . -x ./.venv,./tests
pip-audit -r requirements.txt
```

## Project Structure

| File                       | Purpose                                                       |
|----------------------------|---------------------------------------------------------------|
| `app.py`                   | Flask app with allow list validation                          |
| `tests/test_app.py`        | 12 automated tests                                            |
| `.github/workflows/ci.yml` | The pipeline                                                  |
| `Dockerfile`               | Hardened image                                                |
| `Dockerfile.insecure`      | Intentionally insecure image for comparison only              |
| `compose.yaml`             | Runtime restrictions for Docker Compose                       |
| `k8s/namespace.yaml`       | Namespace enforcing the restricted Pod Security level         |
| `k8s/deployment.yaml`      | Hardened deployment                                           |
| `k8s/service.yaml`         | Fixed address for the app inside the cluster                  |
| `k8s/network-policy.yaml`  | Default deny with one labelled exception                      |
| `k8s/rbac.yaml`            | Read only auditor role                                        |
| `k8s/test-clients.yaml`    | Two test pods used to prove the network policy                |
| `requirements.txt`         | Packages the app needs, the only list copied into the image   |
| `requirements-dev.txt`     | Test and scanning tools, never shipped                        |
| `.gitleaks.toml`           | Secret scanner settings and the documented exception          |
| `evidence/`                | Trivy scan reports from Week 1                                |

## Next Steps

A pipeline step that deploys to a temporary cluster on each change, egress network rules, a scheduled nightly scan, and a multi stage build to shrink the image.
