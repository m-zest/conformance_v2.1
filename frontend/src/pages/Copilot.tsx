import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, useApi } from "../api";
import { useMe } from "../App";
import { BarList, ChartCard, LineChart, StackedColumns } from "../components/charts";
import { InteractionsTable, RequestDrawer } from "../components/detail";
import { Card, Empty, ErrorBox, Note, PageHeader, RangePicker, Stat, UserCell } from "../components/ui";
import { ago, bucketLabel, num, pct } from "../format";

function ConnectorStatus({ connector, onSynced }: { connector: any; onSynced: () => void }) {
  const me = useMe();
  const [busy, setBusy] = useState(false);
  if (!connector) return null;
  const sync = async () => {
    setBusy(true);
    try {
      await api(`/connectors/${connector.id}/sync`, { method: "POST" });
      window.setTimeout(() => { onSynced(); setBusy(false); }, 2500);
    } catch {
      setBusy(false);
    }
  };
  const mode = connector.mode === "live" ? <span className="badge good">Live</span>
    : connector.mode === "demo" ? <span className="badge outline">Demo data from the bundled simulator</span>
    : <span className="badge">Not connected</span>;
  return (
    <div className="row-wrap" style={{ fontSize: 13 }}>
      {mode}
      {connector.mode !== "disabled" && (
        <span className="secondary">
          {connector.last_status === "error" ? `Last sync failed ${ago(connector.last_sync_at)}: ${connector.last_error}` : `Last sync ${ago(connector.last_sync_at)}`}
        </span>
      )}
      {me.role === "admin" && connector.mode !== "disabled" && (
        <button className="btn sm" onClick={sync} disabled={busy} style={{ marginLeft: "auto" }}><RefreshCw size={13} />{busy ? "Syncing" : "Sync now"}</button>
      )}
    </div>
  );
}

function M365({ data, loading, reload }: { data: any; loading: boolean; reload: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const m = data.m365;
  const series = m.series.map((p: any) => ({ label: bucketLabel(p.t, "day"), value: p.requests, flagged: p.flagged }));
  return (
    <div className="stack">
      <ConnectorStatus connector={m.connector} onSynced={reload} />
      <Note>
        Microsoft 365 Copilot cannot be routed through the gateway. Prompts and responses are read from the Microsoft Graph interaction export
        and scanned with the same detectors as gateway traffic. Findings raise the same alerts, but nothing can be masked or blocked here.
        Inline control for Microsoft 365 Copilot is configured in Microsoft Purview.
      </Note>
      {m.connector?.mode === "disabled" ? <Card><Empty title="Connector is not configured">Set M365_COPILOT_MODE and the Entra application credentials. The integration guide lists the steps.</Empty></Card> : (
        <>
          <div className={`grid cols-4 ${loading ? "loading-fade" : ""}`}>
            <Stat label="Interactions" value={num(m.interactions)} />
            <Stat label="Active users" value={num(m.active_users)} />
            <Stat label="Sensitive content" value={num(m.flagged)} />
            <Stat label="Flag rate" value={pct(m.flag_rate)} />
          </div>
          <div className="grid cols-2-1">
            <ChartCard title="Copilot interactions" sub="Prompts per day across Microsoft 365 apps" fade={loading}
              table={{ columns: ["Day", "Interactions", "Flagged"], rows: series.map((p: any) => [p.label, p.value, p.flagged]) }}>
              <LineChart name="Interactions" data={series} />
            </ChartCard>
            <Card title="Where Copilot is used" sub="Interactions by Microsoft 365 app">
              <BarList items={m.by_host.map((h: any) => ({ label: h.host, value: h.interactions, hint: `${h.host}: ${h.interactions} interactions, ${h.flagged} flagged, ${h.users} users` }))} />
            </Card>
          </div>
          <div className="grid cols-2">
            <Card title="What was detected" sub="New sensitive items in Copilot prompts">
              <BarList items={m.categories.map((c: any) => ({ label: c.label, value: c.count }))} empty="Nothing detected in this period" />
            </Card>
            <Card title="People sending the most sensitive content" flush>
              {m.top_users.length === 0 ? <Empty title="Nothing detected in this period" /> : (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>User</th><th className="right">Interactions</th><th className="right">Flagged</th></tr></thead>
                    <tbody>
                      {m.top_users.map((u: any) => (
                        <tr key={u.user.id}><td><UserCell user={u.user} /></td><td className="right num">{u.interactions}</td><td className="right num">{u.flagged}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
          <Card title="Recent Copilot interactions with detected content" flush>
            {m.recent.length === 0 ? <Empty title="Nothing detected in this period" /> : (
              <InteractionsTable items={m.recent} onOpen={setOpen} selected={open} />
            )}
          </Card>
        </>
      )}
      {open && <RequestDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function GitHub({ data, loading, reload }: { data: any; loading: boolean; reload: () => void }) {
  const g = data.github;
  const series = g.series.map((p: any) => ({ ...p, label: bucketLabel(p.t + "T00:00:00Z", "day") }));
  return (
    <div className="stack">
      <ConnectorStatus connector={g.connector} onSynced={reload} />
      <Note>
        GitHub does not make Copilot prompts available to customers, so this view covers adoption and seat usage, not content. To control what
        Copilot can read, use content exclusion in GitHub. To inspect content, route coding assistants that accept a custom endpoint through the gateway.
      </Note>
      {g.connector?.mode === "disabled" ? <Card><Empty title="Connector is not configured">Set GITHUB_COPILOT_MODE, GITHUB_ORG and GITHUB_TOKEN. The integration guide lists the steps.</Empty></Card> : (
        <>
          <div className={`grid cols-4 ${loading ? "loading-fade" : ""}`}>
            <Stat label="Assigned seats" value={num(g.seats)} foot={<span>{g.active_7d} active in the last 7 days</span>} />
            <Stat label="Idle seats (30 days)" value={num(g.inactive_30d)} foot={<span>Candidates to reclaim</span>} />
            <Stat label="Acceptance rate" value={g.acceptance_rate == null ? "No data" : pct(g.acceptance_rate)} />
            <Stat label="Using agent mode" value={num(g.agent_users)} foot={<span>{g.chat_users} using chat</span>} />
          </div>
          <div className="grid cols-2-1">
            <ChartCard title="Daily active Copilot users" fade={loading}
              table={{ columns: ["Day", "Active users", "Chat requests", "Suggestions", "Accepted"], rows: series.map((p: any) => [p.label, p.active_users, p.interactions, p.generations, p.acceptances]) }}>
              <StackedColumns data={series} series={[{ key: "active_users", label: "Active users", color: "var(--series-1)" }]} />
            </ChartCard>
            <Card title="Editors" sub="User-days by editor">
              <BarList items={g.by_ide.map((x: any) => ({ label: x.name, value: x.count }))} empty="No usage reported yet" />
            </Card>
          </div>
          <div className="grid cols-2">
            <Card title="Models" sub="User-days by most used model">
              <BarList items={g.by_model.map((x: any) => ({ label: x.name, value: x.count }))} empty="No usage reported yet" />
            </Card>
            <Card title="Languages" sub="User-days by most used language">
              <BarList items={g.by_language.map((x: any) => ({ label: x.name, value: x.count }))} empty="No usage reported yet" />
            </Card>
          </div>
          <div className="grid cols-3-2">
            <Card title="Usage by developer" flush>
              {g.users.length === 0 ? <Empty title="No usage reported yet" /> : (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Developer</th><th className="right">Active days</th><th className="right">Chat requests</th><th className="right">Accepted</th><th>Model</th><th>Agent</th></tr></thead>
                    <tbody>
                      {g.users.map((u: any) => (
                        <tr key={u.login}>
                          <td>{u.user ? <UserCell user={u.user} /> : <span className="mono">{u.login}</span>}</td>
                          <td className="right num">{u.active_days}</td>
                          <td className="right num">{num(u.interactions)}</td>
                          <td className="right num">{u.generations ? pct((u.acceptances / u.generations) * 100, 0) : ""}</td>
                          <td className="secondary">{u.model}</td>
                          <td className="secondary">{u.agent ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
            <Card title="Idle seats" sub="No activity in the last 30 days" flush>
              {g.inactive.length === 0 ? <Empty title="Every seat is in use" /> : (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Developer</th><th>Last activity</th></tr></thead>
                    <tbody>
                      {g.inactive.map((s: any) => (
                        <tr key={s.login}>
                          <td>{s.user ? <UserCell user={s.user} /> : <span className="mono">{s.login}</span>}</td>
                          <td className="secondary">{s.last_activity_at ? ago(s.last_activity_at) : "Never used"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

export default function Copilot() {
  const [range, setRange] = useState("14d");
  const [tab, setTab] = useState<"m365" | "github">("m365");
  const { data, error, loading, reload } = useApi<any>(`/copilot?range=${range}`, 60000);
  return (
    <div>
      <PageHeader title="Copilot" sub="Oversight of the Copilot products, which run outside the gateway and are observed through their vendor APIs.">
        <RangePicker value={range} onChange={setRange} />
      </PageHeader>
      <div className="tabs" role="tablist">
        <button role="tab" className="tab" aria-selected={tab === "m365"} onClick={() => setTab("m365")}>Microsoft 365 Copilot</button>
        <button role="tab" className="tab" aria-selected={tab === "github"} onClick={() => setTab("github")}>GitHub Copilot</button>
      </div>
      <ErrorBox message={error} />
      {data && (tab === "m365" ? <M365 data={data} loading={loading} reload={reload} /> : <GitHub data={data} loading={loading} reload={reload} />)}
    </div>
  );
}
