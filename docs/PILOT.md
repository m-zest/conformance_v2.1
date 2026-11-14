# Pilot plan

A practical plan for introducing Conformance with one internal tool and a small group of users, then expanding to the rest of the company.

## Before you start: legal and people

Conformance records what employees send to AI tools. Sort out the following first. Skipping it is the most common reason a pilot like this is stopped.

| Topic | What to do |
|---|---|
| Legal basis | Document why the monitoring is necessary and proportionate. In the EU this normally means a legitimate interest assessment and, given the scale, a data protection impact assessment |
| Employee representatives | Where a works council or union exists, consult it before any monitoring starts. In several EU countries this is a legal requirement, not a courtesy |
| Transparency | Tell employees what is recorded, why, who can see it and for how long. Update the acceptable use policy for AI tools |
| Data minimisation | Keep `STORE_PROMPTS=redacted` (the default) or `none`. Agree the retention period and set `RETENTION_DAYS` |
| Access | Decide who gets a dashboard account and in which role. Keep the group small |
| Purpose limitation | State that the data is used for security and compliance, not for performance evaluation |

Involve the privacy officer and the security lead from the first day. This document is not legal advice.

## Roles

| Role | Responsibility |
|---|---|
| Sponsor | Owns the decision to proceed and the budget |
| Pilot owner | Runs the pilot day to day, reports results |
| Platform engineer | Installs and operates the gateway |
| Tool owner | Changes the pilot tool's configuration and tests it |
| Security analyst | Triages alerts, tunes rules |
| Privacy officer | Reviews storage, retention and communication |

## Phases

### Phase 0: Preparation (1 to 2 weeks)

- Complete the legal steps above.
- Choose one internal tool that calls a model through an API and has an owner willing to change one setting.
- Choose 10 to 20 users from two or three teams, including at least one team that handles personal data.
- Install Conformance in demo mode and walk the stakeholders through the dashboard with the synthetic data.

### Phase 1: Monitor (2 weeks)

- Install clean (see [INSTALL.md](INSTALL.md), "From demo to pilot").
- Register the tool with the **Monitor only** policy. Nothing is changed or blocked.
- Connect the tool. Confirm that requests appear under Activity with the right user and team.
- Configure one notification channel for the analyst.
- Review alerts daily. Mark false positives. Note which categories are noise for this tool.

Output of this phase: a list of what was found, the false positive rate per category, and the number of requests enforcement would have masked or blocked (shown on the overview as "would have enforced").

### Phase 2: Enforce (2 weeks)

- Adjust the policy from what you learned: ignore noisy categories, add custom terms for your own confidential names.
- Tell the pilot users what will change and what a blocked message looks like.
- Switch the tool to an enforcing policy. Start with blocking credentials and masking financial and identity data.
- Watch for complaints and for blocked requests that should have passed.

### Phase 3: Expand (ongoing)

In this order:

1. More users on the pilot tool.
2. More internal tools, each starting in monitor mode.
3. Developer tools (Claude Code, Codex) through managed configuration. Expect more findings and plan a longer monitor period.
4. The Microsoft 365 Copilot and GitHub Copilot connectors.
5. Single sign-on for developer tools, directory synchronisation, TLS and backups if not already in place.

## Success criteria

Agree these before Phase 1 and measure them at the end of Phase 2.

| Criterion | How to measure | Example target |
|---|---|---|
| Coverage | Share of the pilot tool's traffic that passes through the gateway | 100 percent |
| Attribution | Share of interactions with an identified user | Above 99 percent |
| Added latency | Gateway overhead on the overview page | Median under 10 ms, 95th percentile under 50 ms |
| Detection quality | False positive alerts divided by all closed alerts | Under 10 percent after tuning |
| Protection | Credentials and regulated personal data reaching the provider in enforce mode | None |
| User impact | Complaints about wrongly blocked requests | Fewer than one per 1,000 requests |
| Triage effort | Analyst time per week | Under two hours for the pilot group |
| Auditability | Ledger verification | Passes. An export can be produced on request |

## What to report at the end

- Usage: users, interactions, tools, estimated spend.
- Risk found: sensitive items by category, credentials blocked, top sources by team.
- Quality: false positive rate, changes made to policies and rules.
- Operations: uptime, latency, incidents.
- Recommendation: which tools to onboard next, which policy for each, and what needs to be in place first.

The overview and the people pages provide most of these numbers. The audit export provides the record-level data.

## Communication template

Adapt this for the pilot users.

> From [date], requests you send to [tool name] pass through a company AI gateway before they reach the AI provider. The gateway checks them for personal data, credentials and confidential information, to protect our customers and the company.
>
> What is recorded: who sent a request, when, to which tool, and which kinds of sensitive data were found. The text is stored with sensitive values removed. Records are kept for [n] days and can be seen only by [roles].
>
> What changes for you: for the first two weeks, nothing. After that, some sensitive values will be replaced by placeholders before the request is sent, and requests that contain passwords or access keys will be stopped with a message explaining why.
>
> This data is used for security and compliance only. It is not used to assess individual performance. Questions: [contact].
