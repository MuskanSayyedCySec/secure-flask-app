# Secure Flask App

A small Python web app packaged in a hardened Docker container. I built an insecure version first, measured its problems, then hardened it step by step and proved each control works with tests and scans.

## Why

Containers are often built from large base images, run as root and carry secrets inside them. This project shows how much risk that adds, and how much can be removed with secure defaults, least privilege and evidence based fixes.

## Results

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
| Security tests passed          |              | 5 of 5                |

## Principles Applied

| Principle                   | Where                                                                                     | Proof                                                                 |
|-----------------------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| Secure by default           | Debug off, app listens on 127.0.0.1 unless a container overrides it                       | Flask reports debug mode off                                          |
| Fail securely               | App and compose file refuse to start without a secret                                     | Startup fails with a clear error and no container is created         |
| Least privilege             | Non root user, all capabilities dropped, no new privileges                                | `id` shows UID 10001, `CapBnd` shows all zeros                        |
| Reducing the attack surface | Slim base image, pip removed, Gunicorn control socket disabled                            | Vulnerabilities down 95%, `pip` not found in container                |
| Defence in depth            | Allow list validation plus output escaping, file permissions plus read only file system   | Script tag rejected with 400, root cannot write to the app folder     |
| Immutability                | Read only file system, app code owned by root                                             | Writes fail with "Read-only file system" and "Permission denied"      |
| Availability                | Gunicorn workers, health check, memory, CPU and process limits                            | Container reports healthy, 84 MiB used of a 256 MiB limit             |

## Standards

CIS Docker Benchmark recommendations for a non root user, health checks, no unnecessary packages, a read only root file system, dropped capabilities, no new privileges and resource limits.

NIST SSDF practices for scanning dependencies and fixing known vulnerabilities before release.

OWASP Top 10 risks for injection, including cross site scripting, through input validation, and security misconfiguration through disabled debug mode.

Cyber Essentials secure configuration, by removing software and features the app does not need.

## Key Findings

**All Python vulnerabilities were inside pip.** Every app dependency had zero known vulnerabilities. The 7 Python findings were in libraries pip bundles inside itself, confirmed with pip's own vendor list. Pip is only needed during the build, so I removed it from the final image, which cleared all 7.

**A newer Gunicorn opened an unauthenticated control socket by default.** The non root container blocked it from writing the socket file. Instead of loosening permissions, I disabled the feature because the app does not need it.

**The baked in secret was caught three ways.** Docker's build checks warned about it, `docker inspect` exposed it, and Trivy rated it critical.

**A newline could bypass validation.** In Python, `$` in a regular expression also matches before a trailing newline. Using `fullmatch` closed the gap, and a test proves it.

## Security Tests

| Test           | Expected | Result |
|----------------|----------|--------|
| Health check   | 200      | 200    |
| Valid name     | 200      | 200    |
| Script tag     | 400      | 400    |
| 60 characters  | 400      | 400    |
| Hidden newline | 400      | 400    |

All five passed on the local app, in the hardened container, and again with every runtime restriction switched on.

## Residual Risk

164 vulnerabilities remain in core Debian packages that the slim image needs.

The Server header still shows "gunicorn", although versions are no longer exposed. A reverse proxy could hide it.

A secret passed at runtime can be read by anyone with Docker access on the host. A proper secrets manager would fix this.

Removing pip did not reduce image size, because it lives in a lower layer of the base image. A multi stage build would fix this.

## Tech Stack

Python 3.13, Flask, Gunicorn, Docker, Docker Compose, Trivy, Git

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

To repeat the scans.

```bash
trivy image --scanners vuln flask-app:hardened
trivy config .
```

## Project Structure

| File                  | Purpose                                              |
|-----------------------|------------------------------------------------------|
| `app.py`              | Flask app with allow list validation                 |
| `Dockerfile`          | Hardened image                                       |
| `Dockerfile.insecure` | Intentionally insecure image for comparison only     |
| `compose.yaml`        | Runtime restrictions as code                         |
| `.dockerignore`       | Keeps junk and secret files out of the image         |
| `evidence/`           | Trivy scan reports, before and after                 |

## Next Steps

A multi stage build to shrink the image, and a CI/CD pipeline that runs these scans automatically and blocks insecure code.
