# Security policy

## Supported versions

Chronos has not published its first release. Security fixes currently target the latest commit on `main`; no historical version receives a support guarantee yet.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting flow under the repository's **Security** tab. Include:

- the affected commit or version;
- a minimal reproduction or proof of concept;
- the security impact and required preconditions;
- whether secrets, arbitrary code execution, path handling, resource exhaustion, or scheduler state are involved;
- any suggested mitigation.

Do not open a public issue containing exploit details, secrets, access tokens, or private job data. If private reporting is temporarily unavailable, open a public issue asking for a private contact channel without including vulnerability details.

You should receive an acknowledgement within seven days. Validation, remediation, disclosure timing, and credit will be coordinated through the private report.

## Security boundary

Chronos executes trusted Nox handlers with the full authority of the host process. It is not a sandbox and does not evaluate job definitions as code. The core does not expose a network listener, shell-string executor, remote administration interface, or implicit persistence.

See [docs/security.md](docs/security.md) for the complete threat model and resource bounds.
