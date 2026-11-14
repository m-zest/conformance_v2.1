# Integrations

How to bring each kind of AI tool under governance. Start with one internal tool, then developer tools, then the Copilot connectors.

| Tool | Method | What you get | Effort |
|---|---|---|---|
| [Internal applications](#1-internal-applications) | Point the base URL at the gateway | Inline log, mask and block | One configuration change and one header |
| [Claude Code](#2-claude-code) | Environment settings pushed by IT | Inline log, mask and block | Managed settings file |
| [Codex CLI](#3-codex-cli) | Provider entry in the Codex configuration | Inline log, mask and block | Managed configuration file |
| [Other OpenAI-compatible clients](#4-other-clients) | Custom endpoint where the client allows it | Inline, for the traffic the client routes | Varies |
| [Microsoft 365 Copilot](#5-microsoft-365-copilot) | Connector on the Microsoft Graph export | Content scanning and alerts after the fact | Entra app registration |
| [GitHub Copilot](#6-github-copilot) | Connector on seat and usage reports | Adoption and licence oversight, no content | Token or GitHub App |
| [Unmanaged AI websites](#7-unmanaged-ai-websites) | Your existing web proxy or CASB | Discovery and blocking | Outside this product |

## How users are identified

You do not hand out a key per person. Identity comes from what people already use.

| Pattern | For | How it works |
|---|---|---|
| **Trusted application** | Internal web applications | The application holds one gateway key. Employees sign in to the application as they do today. The application sends the signed-in user's address with each call in `X-End-User`. One key covers any number of users |
| **Personal key** | A developer's own machine, scripts | A key bound to one person. Created under Tools with "Bind to one user" |
| **SSO token** | Developer tools at scale | The tool obtains a token from your identity provider and sends it as the bearer token. The gateway verifies it against the provider's published keys and reads the user from its claims. Nobody handles long-lived keys |

Team and job title are read from the `X-End-User-Team` header, from token claims, or loaded in bulk:

```bash
curl -X POST https://<dashboard>/api/users/import -b <session cookie> -H "Content-Type: application/json" \
  -d '[{"email": "name@company.com", "name": "Full Name", "team": "Finance", "github_login": "their-handle"}]'
```

## 1. Internal applications

Any application that calls a model through the OpenAI or Anthropic API.

**In the dashboard**

1. **Tools, Register tool.** Choose the "Monitor only" policy to begin with.
2. Open the tool and create a key. Copy it: it is shown once.
3. Leave "Trust asserted user" on if the application authenticates its own users.

**In the application**

Change the base URL and the key, and add the user headers. Nothing else changes.

```python
import openai

client = openai.OpenAI(base_url="https://ai-gateway.company.com/v1", api_key=GATEWAY_KEY)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    extra_headers={
        "X-End-User": session.user.email,        # from your session, never from user input
        "X-End-User-Name": session.user.name,
        "X-End-User-Team": session.user.department,
    },
)
```

With the Anthropic SDK:

```python
import anthropic

client = anthropic.Anthropic(base_url="https://ai-gateway.company.com", api_key=GATEWAY_KEY)
message = client.messages.create(
    model="claude-sonnet-4-5", max_tokens=1024, messages=messages,
    extra_headers={"X-End-User": session.user.email},
)
```

**Endpoints**

| Endpoint | Protocol |
|---|---|
| `POST /v1/chat/completions` | OpenAI chat completions, with streaming |
| `POST /v1/responses` | OpenAI responses, with streaming |
| `POST /v1/messages` | Anthropic messages, with streaming |
| `POST /v1/messages/count_tokens`, `GET /v1/models` | Passed through |

The key is accepted as `Authorization: Bearer <key>`, `x-api-key: <key>` or `api-key: <key>`, so existing SDKs work unchanged.

**What the application should handle**

| Response | Meaning | What to do |
|---|---|---|
| Normal response | Allowed, or masked before forwarding | Nothing. The headers `x-conformance-action` and `x-conformance-findings` tell you what happened if you want to show it |
| `403` with error type `policy_violation` | Blocked by policy | Show the message to the user. It names what to remove and includes a reference ID |
| `401` | Key missing, wrong or revoked | Configuration problem |
| `502` | The provider is unreachable from the gateway | Retry, then alert operations |

If a message is blocked, do not add it to the conversation history you resend, otherwise every later turn is blocked too. The sample tool in `demo-app/` shows this.

**Retrieval and tools.** Text that your application adds to the request (retrieved documents in the system prompt, tool results) is scanned like user input. This is where confidential documents usually enter.

**Downstream services you operate.** If the application or the model calls your own MCP servers or APIs, they can require the gateway's compliance token. See `sdk/conformance_verifier.py`.

## 2. Claude Code

Claude Code supports routing through a gateway with environment variables. Push them with your device management tool in the managed settings file so users cannot remove them.

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://ai-gateway.company.com",
    "ANTHROPIC_AUTH_TOKEN": "<gateway key or SSO token>"
  }
}
```

- `ANTHROPIC_AUTH_TOKEN` is sent as a bearer token. Use a personal gateway key per developer, or configure `apiKeyHelper` to return a fresh SSO token so that no long-lived key sits on laptops.
- Register one tool in the dashboard for developer tools (the demo calls it "Developer Tools") and assign its policy. With SSO tokens set `OIDC_DEFAULT_APP` to its identifier.
- The gateway forwards to your Anthropic endpoint with the organisation key. Developers no longer need provider keys.

Start coding assistants in **monitor** mode. They send source files, logs and configuration, which contain many strings that look sensitive and some that are. Review two weeks of findings before enforcing, then block credentials first.

Check the current Claude Code documentation for the exact managed settings location on each operating system.

## 3. Codex CLI

Add a provider to the Codex configuration (`~/.codex/config.toml`, or the managed configuration your IT team distributes):

```toml
model_provider = "conformance"

[model_providers.conformance]
name = "Company AI gateway"
base_url = "https://ai-gateway.company.com/v1"
env_key = "CONFORMANCE_GATEWAY_KEY"
wire_api = "responses"
```

Set `CONFORMANCE_GATEWAY_KEY` to the developer's personal gateway key or SSO token. The gateway's `/v1/responses` endpoint handles the traffic.

## 4. Other clients

Any client that lets you set an OpenAI-compatible or Anthropic-compatible endpoint can be governed the same way: agent frameworks, notebooks, IDE extensions with a custom provider, command line tools. Two cautions:

- Some products send only part of their traffic to a custom endpoint and keep the rest on their own backend. Test what actually arrives under Activity before relying on it.
- A user can only bypass the gateway if they hold a provider key. Keeping provider keys exclusively on the gateway is what makes routing enforceable.

## 5. Microsoft 365 Copilot

Microsoft 365 Copilot runs inside Microsoft's service and cannot be routed. The connector reads the prompts and responses afterwards from the Microsoft Graph AI interaction export and scans them with the same detectors. Findings appear under Activity, raise alerts, and feed the Copilot page.

**What you get:** who uses Copilot in which Microsoft 365 application, what sensitive content was put into prompts, alerts on it, and the same risk scoring as for governed tools.

**What you do not get:** blocking or masking. For inline control of Microsoft 365 Copilot use Microsoft Purview (data loss prevention for Copilot, sensitivity labels). The two complement each other: Purview enforces inside Microsoft 365, Conformance gives you one view across all AI tools.

### Setup

1. In the Microsoft Entra admin centre, create an **app registration** for Conformance.
2. Under **API permissions**, add these Microsoft Graph **application** permissions and grant admin consent:
   - `AiEnterpriseInteraction.Read.All` to read Copilot interactions
   - `User.Read.All` to list users with their department and job title
3. Under **Certificates and secrets**, create a client secret.
4. In `.env`:

   ```bash
   M365_COPILOT_MODE=live
   M365_TENANT_ID=<directory (tenant) ID>
   M365_CLIENT_ID=<application (client) ID>
   M365_CLIENT_SECRET=<client secret value>
   ```

5. `docker compose up -d`, then open **Copilot** in the dashboard and choose **Sync now**. The first run imports the last 14 days (`M365_LOOKBACK_DAYS`). Imported history raises alerts in the dashboard but does not send notifications.

The connector calls, for each user:

```text
GET https://graph.microsoft.com/v1.0/copilot/users/{id}/interactionHistory/getAllEnterpriseInteractions
    ?$filter=createdDateTime gt {since} and createdDateTime lt {until}
```

Users without a Copilot licence are skipped.

### Notes for the first live run

- This connector was developed against the Microsoft documentation and tested with the bundled simulator, not yet against a production tenant. Run the first sync while watching `docker compose logs -f gateway`.
- A `403` from Graph usually means admin consent is missing or the permission was added as delegated instead of application.
- The export covers interactions of users licensed for Microsoft 365 Copilot. Check Microsoft's current documentation for licensing and any metering that applies to this API.
- Before enabling it, agree with your privacy officer and employee representatives that Copilot prompts will be analysed. The connector stores redacted prompts only, like the gateway.
- The code is in `backend/app/connectors/m365_copilot.py`. Field mapping is in one place if Microsoft changes the response.

### Going further

- The Purview audit log records which files and sensitivity labels a Copilot interaction touched. Importing it is on the roadmap.
- Graph change notifications could replace polling for near real time alerts.

## 6. GitHub Copilot

GitHub does not make Copilot prompts or completions available to customers on the Business and Enterprise plans, so no connector can inspect content. The connector provides the oversight that is possible:

- **Seats:** who has a licence, when they last used it and in which editor. Idle seats are listed so they can be reclaimed.
- **Usage:** daily active developers, chat requests, suggestion acceptance, agent mode adoption, editors, languages and models.

### Setup

1. Create a token that can read Copilot data for your organisation: a fine-grained personal access token or a GitHub App with read access to **GitHub Copilot Business** and organisation members. An organisation owner must approve it.
2. In the organisation's Copilot policies, enable access to **Copilot usage metrics**.
3. In `.env`:

   ```bash
   GITHUB_COPILOT_MODE=live
   GITHUB_ORG=<organisation login>
   GITHUB_TOKEN=<token>
   ```

4. `docker compose up -d`, then **Copilot, GitHub Copilot, Sync now**.

The connector reads `GET /orgs/{org}/copilot/billing/seats` and the per-user daily usage reports, which return download links to newline-delimited JSON files.

GitHub replaced its earlier Copilot metrics API in 2026. The usage report path and the API version are therefore settings: `GITHUB_USAGE_REPORT_PATH` (default `/orgs/{org}/copilot/metrics/reports/users-1-day`) and `GITHUB_API_VERSION`. Confirm both against the current GitHub REST reference before the first live run. The seats part does not depend on them. As with Microsoft 365, the connector has been tested against the simulator only. For GitHub Enterprise Server or data residency set `GITHUB_API_URL`.

**Matching developers to employees.** GitHub reports logins, not corporate addresses. Load the mapping once with the user import shown at the top of this page (`github_login`). Unmatched logins are shown as they are.

### Controlling content in GitHub Copilot

Since content cannot be observed, control it at the source:

| Option | What it does |
|---|---|
| Content exclusion (GitHub setting) | Keeps chosen repositories, paths and file types out of Copilot's context |
| Secret scanning and push protection | Catches credentials in code regardless of how they got there |
| A custom model endpoint, where your Copilot plan offers one | Chat requests to that model can be pointed at the gateway and are then governed like any other tool. Check what your plan supports and test what arrives |
| Network inspection | Copilot supports an HTTP proxy with a custom certificate. A TLS-inspecting proxy can see the traffic. This is intrusive and needs legal review |
| A governed alternative | Offer developers a coding assistant routed through the gateway for work on sensitive repositories |

## 7. Unmanaged AI websites

People pasting company data into personal accounts on public AI websites is outside what a gateway can see. Use the controls you already have:

- **Discovery:** web proxy, DNS or CASB reports show which AI sites are used and by whom.
- **Policy:** allow the sanctioned tools, block or warn on the rest.
- **Alternative:** the most effective measure is a sanctioned tool that is as convenient. An internal assistant behind the gateway gives people a place where the same work is allowed.

## Adding a connector

A connector is a class with an `id` and an async `sync(connector)` method that returns the number of items stored. For tools that expose content, build a `Record` and call `recorder.persist()`: detection, the ledger and alert rules then apply automatically. See `backend/app/connectors/m365_copilot.py` for a complete example, and register the class in `backend/app/connectors/scheduler.py`.
