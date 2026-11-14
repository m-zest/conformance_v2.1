# Roadmap

What is deliberately not in the pilot version, why, and what it would take. Items are grouped by theme and ordered by expected value within each group.

## Trust and cryptography

These items extend the compliance checking and signing design towards a service that other parties can rely on without trusting the operator.

| Item | Why it is not in the pilot | What it involves |
|---|---|---|
| **Signing key in a KMS or HSM** | A file-based key is sufficient while the gateway and its verifiers belong to one team | Replace the local key in `signing.py` with calls to a key service (cloud KMS, or PKCS#11 for an HSM). The private key then never exists in gateway memory. Add key rotation with overlapping key IDs in the JWKS |
| **Trusted execution environment for the checker** | It addresses a threat the pilot does not have: an operator of the gateway reading prompts. It also needs specific hardware and adds operational cost | Run the detection and signing step inside a confidential computing environment (for example AMD SEV-SNP or Intel TDX confidential VMs, or an enclave runtime). Publish the measured image so that verifiers can check, through remote attestation, that the token was issued by the expected code. Bind the attestation report to the signing key |
| **Attested tokens** | Depends on the two items above | Include an attestation reference in the token or the JWKS so a verifier can establish that the key is held inside an attested environment |
| **External ledger anchoring** | The in-database chain already detects edits by anyone who cannot rewrite and re-sign all of it | Publish the ledger head hash on a schedule to a separate system: a write-once bucket, a transparency log or a timestamping service |
| **Privacy-preserving checks** | Research topic | Evaluate how much of the checking can be done without the checker seeing plaintext, and measure what leaks through timing and size side channels |
| **Signed responses** | Not needed for the monitoring use case | Sign the model output too, so downstream systems can verify which model and policy produced a piece of content. This is the C2PA-style provenance direction |

## Detection

| Item | Notes |
|---|---|
| File and image scanning | Extract text from PDF and Office attachments and run OCR on images before scanning |
| Exact data matching | Match against hashed copies of your real customer identifiers, so detection does not depend on format |
| Dedicated injection classifier | A small model such as Prompt Guard behind the existing guard interface, for higher recall than heuristics |
| More national identifiers and languages | Additional checksum-validated formats and multilingual entity models |
| Response enforcement | Mask or stop sensitive content in model responses, including while streaming |
| Reversible masking | Replace placeholders in the model's answer with the original values before returning it to the user, so masked requests remain fully useful |
| Feedback loop | Use false positive markings to adjust confidence per pattern and per tool automatically |

## Governance features

| Item | Notes |
|---|---|
| Model allow-list and routing | Restrict each tool to approved models and route by data sensitivity, for example personal data only to a provider in the EU or to a self-hosted model |
| Budgets and rate limits | Per tool, team and user, with alerts before a limit is reached |
| Policy approval workflow | Require a second person to approve a policy change |
| Regulatory mapping | Tag tools with their risk classification and obligations under the EU AI Act and produce the corresponding evidence report |
| Purview audit import | Add which files and sensitivity labels a Microsoft 365 Copilot interaction touched |
| More connectors | ChatGPT Enterprise compliance export, Google Gemini for Workspace, others as needed |
| Browser extension or proxy integration | Visibility into unmanaged AI websites |

## Identity and access

| Item | Notes |
|---|---|
| Single sign-on for the dashboard | OIDC or SAML login in place of local accounts |
| Directory synchronisation | SCIM or scheduled import from the identity provider for teams, managers and leavers |
| Scoped analyst access | Limit an analyst to certain teams or tools |
| Break-glass access to originals | A logged, approved procedure to see unredacted content for an investigation, if your policy allows storing it |

## Operations

| Item | Notes |
|---|---|
| Schema migrations | Introduce Alembic so upgrades are safe across schema changes |
| High availability | Several gateway replicas behind a load balancer, with the scheduler and retention job on one worker. The ledger writer is already safe for multiple writers |
| Durable record queue | Write records through a durable queue so a crash cannot lose records in flight |
| Metrics and tracing | Prometheus metrics and OpenTelemetry traces for the gateway itself |
| Load and cost benchmarks | Published figures for latency, throughput and cost per million requests on reference hardware |
| Kubernetes packaging | A Helm chart alongside the Compose file |
| SIEM formats | Alert output in CEF or OCSF in addition to the generic webhook |
