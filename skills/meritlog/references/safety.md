# Confidentiality rules (apply to every entry and every compiled line)

**Default stance:** the log is written as if it will be read by a recruiter at a competitor. If in doubt, generalize; if you can't generalize safely, leave it out and add 1 to `omitted`.

## Never record

| Category | Examples of what must NOT appear |
|----------|----------------------------------|
| Customers & partners | Customer names, logos, deal sizes, anything identifying a specific account |
| People | Colleagues' names, handles, emails; who caused an incident |
| Internal identifiers | Hostnames, internal domains/URLs, IPs, repo names, service names, cluster/account/project IDs, ticket keys, Slack channels |
| Codenames | Internal project or product codenames, unreleased product names or features |
| Secrets | Keys, tokens, passwords, certificates, anything that looks like one, even if revoked |
| Vulnerabilities | Anything unfixed; any bypass or exploit detail; detection gaps; specific CVE-to-system mappings |
| Architecture | Network layout, trust boundaries, auth flows, where sensitive data lives, specific tool configurations or detection rules |
| Incidents | Details that identify a non-public incident (date + impact + system); attacker techniques that worked |
| Business | Revenue, costs, headcount, layoffs, roadmap, audit findings, legal matters |

## How to generalize

| Instead of | Write |
|-----------|-------|
| "Acme Bank's tenant" | "a large financial-services customer" |
| `vault-prod-3.int.example.net` | "the secrets management platform" |
| "Project Falcon" | "a new device-cloud product" |
| "Fixed SSRF in `img-proxy` letting attackers reach the metadata API" | "Remediated a high-severity SSRF vulnerability in an internal service" |
| "Our Splunk rule for X misses Y" | (omit; it describes a detection gap) |
| "Incident on 2026-03-04 exposed 12k sessions" | "Led response to a security incident; contained it and drove the post-incident fixes" |
| "Rolled out to all 412 repos in org `foo`" | "Rolled out across ~400 repositories" (counts are fine; round them, no names) |

## Allowed

- Widely used public technologies and vendors in generic terms (AWS, Kubernetes, Terraform, Okta, Semgrep, GitHub Actions) but **not** how they're configured.
- Public frameworks and standards (SOC 2, ISO 27001, OWASP, MITRE ATT&CK) and the user's role in them, without audit findings.
- Rounded metrics and scope ("~40 services", "cut triage time ~50%") only when the source states them.
- Public work: published CVEs credited to the user, talks, blog posts, open source.

## Self-check before writing any file

1. Could someone identify a customer, colleague, system or incident from this?
2. Does anything describe a weakness that might still exist?
3. Would an attacker learn anything useful about the environment?
4. Is any number more precise than it needs to be?
5. Taken together, do the entries reveal more than each does alone?

Any "yes" → generalize or omit, then check again.
