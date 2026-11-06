# Secure Flask App

![CI](https://github.com/MuskanSayyedCySec/secure-flask-app/actions/workflows/ci.yml/badge.svg)

A small Python web app packaged in a hardened Docker container, with a DevSecOps pipeline that tests and scans every change and blocks anything insecure from reaching the main branch.

Week 1 hardened the container. Week 2 automated every check in GitHub Actions and locked the main branch behind them.

## Why

Containers are often built from large base images, run as root and carry secrets inside them. Manual checks catch some of this, but only when someone remembers to run them. This project shows how much risk can be removed with secure defaults and least privilege, and how a pipeline can enforce those controls on every change so they cannot quietly disappear.

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

Every push to main and every pull request runs three jobs in GitHub Actions.

| Job                   | Checks                                                                                    | Blocks the merge when                                          |
|-----------------------|-------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Run tests             | 12 pytest tests, Bandit code scan, pip-audit dependency scan                              | A test fails, risky code is found, or a package is vulnerable  |
| Scan for secrets      | Gitleaks over the full Git history                                                        | Any secret is found                                            |
| Build and check image | Docker build, non root check, pip absence check, Trivy image and Dockerfile scans         | Root user, pip present, a fixable high or critical vulnerability, or a serious Dockerfile problem |

The build job only runs if the other two pass, so insecure code is never built into an image.

## Pipeline Results

| Test                                                  | Result                                                        |
|-------------------------------------------------------|---------------------------------------------------------------|
| Reintroduced a validation bug in a pull request       | Caught in 10 seconds, 1 failed and 11 passed, build skipped   |
| Committed a fake API key in a pull request            | Caught by both Bandit and Gitleaks, build skipped             |
| Merged the pull request with failing checks           | Refused by the branch ruleset                                 |
| Merged it using administrator privileges              | Refused, the ruleset has no bypass list                       |
| Pushed directly to main                               | Rejected, changes must come through a pull request            |
| Fixable high or critical vulnerabilities in the image | 0 on 6 November 2026 (186 total, 49 high with no fix yet)     |

## Principles Applied

| Principle                   | Where                                                                                         | Proof                                                                  |
|-----------------------------|-----------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| Shift left                  | Every check runs on each pull request, before code reaches main                               | The fake key was caught before merge                                   |
| Failing securely            | Any failed check stops the pipeline, and the build waits for tests and secret scanning       | Build skipped on both failed pull requests                             |
| Separation of duties        | Main is locked behind a ruleset, changes need a pull request with all checks green            | Direct push and admin merge both refused                               |
| Defence in depth            | Four scanners looking at code, packages, history and the image                                | Two independent tools caught the same fake key                         |
| Least privilege             | Non root container, pipeline token limited to read only, credentials not kept on the runner  | `contents: read` and `persist-credentials: false` in the workflow     |
| Integrity                   | Actions pinned to full commit codes, Gitleaks and Trivy verified by SHA256 before running     | A changed download fails the hash check and never runs                 |
| Secure by default           | Debug off, app listens on 127.0.0.1 unless a container overrides it                           | Automated test confirms debug mode is off                              |
| Reducing the attack surface | Slim base image, pip removed, test tools kept out of the image                                | Pipeline confirms pip is absent on every build                         |

## Standards

NIST SSDF practices for automated testing, dependency scanning, secret scanning and protecting the build pipeline.

OWASP Top 10 risks for injection, including cross site scripting, through input validation tests, and security misconfiguration through debug mode and Dockerfile checks.

CIS Docker Benchmark recommendations for a non root user, health checks, no unnecessary packages, a read only root file system and dropped capabilities.

## Key Findings

**Scanners make mistakes in both directions.** Gitleaks flagged a public GPG key fingerprint from the Python base image six times, and Bandit flagged ten safe uses of assert and subprocess in the tests. Both were reviewed and resolved with documented exceptions, one exact value allowed in `.gitleaks.toml` and the test folder excluded from Bandit. A fake secret made of readable words was not flagged at all, which is why the pipeline uses several tools.

**A pipeline that warns is not one that blocks.** Before the ruleset, a failing pull request could still be merged. After it, nothing reaches main unless every check is green, including for the repository owner.

**Scan results go out of date.** The same image went from 164 to 186 known vulnerabilities in 12 days without any code change, because new vulnerabilities were published. Scanning on every build catches this.

**The pipeline itself is a target.** In March 2026, attackers moved version tags on Trivy's GitHub Actions to malicious code. This pipeline pins actions to commit codes and checks downloaded tools against known hashes.

## Documented Exceptions

| Exception                                   | Reason                                                                  |
|---------------------------------------------|-------------------------------------------------------------------------|
| Public GPG key allowed in `.gitleaks.toml`  | It is the Python release signing key fingerprint, public by design      |
| Tests folder excluded from Bandit           | Tests use assert and a fixed subprocess call by design, and never ship  |
| `Dockerfile.insecure` skipped by Trivy      | Intentionally insecure, kept only for the before and after comparison   |
| Unfixed vulnerabilities reported, not blocked | No fix exists yet, so blocking would stop every build with no way forward |

## Residual Risk

186 vulnerabilities remain in core Debian packages, none critical and none with a fix available on 6 November 2026.

Working alone, pull requests need zero human approvals. In a team, at least one reviewer other than the author should be required.

Scanners match patterns and can miss secrets that do not look random.

A secret passed at runtime can be read by anyone with Docker access on the host.

## Tech Stack

Python 3.13, Flask, Gunicorn, Docker, Docker Compose, GitHub Actions, pytest, Bandit, pip-audit, Gitleaks, Trivy, Git

## How to Run

You need Docker Desktop.

```bash
git clone https://github.com/MuskanSayyedCySec/secure-flask-app.git
cd secure-flask-app
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build
```

Then in another terminal.

```bash
curl -i http://127.0.0.1:8080/health
```

To run the tests and scanners locally.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
bandit -r . -x ./.venv,./tests
pip-audit -r requirements.txt
```

## Project Structure

| File                       | Purpose                                                   |
|----------------------------|-----------------------------------------------------------|
| `app.py`                   | Flask app with allow list validation                      |
| `tests/test_app.py`        | 12 automated tests                                        |
| `.github/workflows/ci.yml` | The pipeline                                              |
| `Dockerfile`               | Hardened image                                            |
| `Dockerfile.insecure`      | Intentionally insecure image for comparison only          |
| `compose.yaml`             | Runtime restrictions as code                              |
| `requirements.txt`         | Packages the app needs, the only list copied into the image |
| `requirements-dev.txt`     | Test and scanning tools, never shipped                    |
| `.gitleaks.toml`           | Secret scanner settings and the documented exception      |
| `.dockerignore`            | Keeps junk and secret files out of the image              |
| `evidence/`                | Trivy scan reports from Week 1                            |

## Next Steps

A scheduled nightly scan to catch newly published vulnerabilities between changes, a multi stage build to shrink the image, and a Kubernetes deployment driven by the pipeline.
