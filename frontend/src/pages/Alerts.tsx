import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { api, query, useApi } from "../api";
import { useMe } from "../App";
import { FindingsTable, RedactedText } from "../components/detail";
import { ActionBadge, Card, Drawer, Empty, ErrorBox, PageHeader, SeverityBadge, SourceLabel, StatusBadge, UserCell } from "../components/ui";
import { ago, fullDateTime, titleCase } from "../format";

const TABS: [string, string][] = [
  ["open", "Open"], ["acknowledged", "Acknowledged"], ["resolved", "Resolved"], ["false_positive", "False positive"], ["all", "All"],
];

function AlertDetail({ id, onChanged }: { id: string; onChanged: () => void }) {
  const me = useMe();
  const { data: alert, error, reload } = useApi<any>(`/alerts/${id}`);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const canTriage = me.role !== "auditor";
  if (error) return <ErrorBox message={error} />;
  if (!alert) return null;

  const update = async (body: Record<string, unknown>) => {
    setBusy(true);
    setFailure(null);
    try {
      await api(`/alerts/${id}`, { body: { ...body, note: note || undefined } });
      setNote("");
      await reload();
      onChanged();
    } catch (e) {
      setFailure((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="row-wrap" style={{ marginBottom: 12 }}>
        <SeverityBadge level={alert.severity} />
        <StatusBadge status={alert.status} />
        <SourceLabel source={alert.source} />
      </div>
      <p style={{ fontSize: 14 }}>{alert.summary}</p>

      <div className="section-title">Details</div>
      <dl className="kv">
        <dt>User</dt><dd><UserCell user={alert.user} /></dd>
        <dt>Tool</dt><dd>{alert.app?.name ?? "Unknown"}</dd>
        <dt>Detected</dt><dd>{alert.entity_types.map(titleCase).join(", ")}</dd>
        <dt>First seen</dt><dd>{fullDateTime(alert.created_at)}</dd>
        <dt>Last seen</dt><dd>{fullDateTime(alert.last_seen_at)}</dd>
        <dt>Occurrences</dt><dd className="num">{alert.occurrences}</dd>
        <dt>Assigned to</dt><dd>{alert.assignee ?? <span className="muted">Nobody</span>}</dd>
      </dl>

      {canTriage && (
        <>
          <div className="section-title">Triage</div>
          <textarea className="textarea" rows={2} placeholder="Add a note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="row-wrap" style={{ marginTop: 8 }}>
            {alert.status === "open" && <button className="btn" disabled={busy} onClick={() => update({ status: "acknowledged", assignee: me.email })}>Acknowledge and assign to me</button>}
            {alert.status !== "resolved" && <button className="btn primary" disabled={busy} onClick={() => update({ status: "resolved" })}>Resolve</button>}
            {alert.status !== "false_positive" && <button className="btn" disabled={busy} onClick={() => update({ status: "false_positive" })}>False positive</button>}
            {(alert.status === "resolved" || alert.status === "false_positive") && <button className="btn" disabled={busy} onClick={() => update({ status: "open" })}>Reopen</button>}
            {note && <button className="btn ghost" disabled={busy} onClick={() => update({})}>Save note only</button>}
          </div>
          <ErrorBox message={failure} />
        </>
      )}

      {alert.request && (
        <>
          <div className="section-title">Most recent interaction</div>
          <div className="row-wrap" style={{ marginBottom: 8 }}>
            <ActionBadge action={alert.request.action} would={alert.request.would_action} />
            <span className="muted" style={{ fontSize: 12.5 }}>{fullDateTime(alert.request.ts)}</span>
            <Link to={`/activity?id=${alert.request.id}`} className="row" style={{ marginLeft: "auto", fontSize: 13 }}>
              Open interaction <ExternalLink size={13} />
            </Link>
          </div>
          <RedactedText text={alert.request.prompt_text} />
          <div className="card" style={{ marginTop: 10 }}><FindingsTable findings={alert.request.findings} /></div>
        </>
      )}

      <div className="section-title">History</div>
      <ul className="timeline">
        {alert.events.map((e: any, i: number) => (
          <li key={i}>
            <span style={{ fontWeight: 500 }}>{titleCase(e.action)}</span> by {e.actor}
            <span className="muted"> on {fullDateTime(e.ts)}</span>
            {e.note && <div className="secondary">{e.note}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Alerts() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");
  const [source, setSource] = useState("");
  const { data, error, loading, reload } = useApi<any>(`/alerts${query({ status, severity, source, limit: 200 })}`, 20000);
  const counts = data?.counts ?? {};
  const total = Object.values(counts).reduce((a: number, b: any) => a + Number(b), 0);

  return (
    <div>
      <PageHeader title="Alerts" sub="Raised when new sensitive content is sent to an AI tool. Repeats of the same rule, user and tool on one day are grouped into one alert." />
      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" className="tab" aria-selected={status === key} onClick={() => setStatus(key)}>
            {label}<span className="count">{key === "all" ? total : counts[key] ?? 0}</span>
          </button>
        ))}
      </div>
      <div className="filters">
        <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)} aria-label="Minimum severity">
          <option value="">Any severity</option>
          <option value="critical">Critical only</option>
          <option value="high">High and above</option>
          <option value="medium">Medium and above</option>
        </select>
        <select className="select" value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
          <option value="">All sources</option>
          <option value="gateway">Gateway</option>
          <option value="m365_copilot">Microsoft 365 Copilot</option>
        </select>
      </div>
      <ErrorBox message={error} />
      <Card flush className={loading && !data ? "loading-fade" : ""}>
        {data && data.items.length === 0 ? <Empty title="No alerts here">Nothing matches the current filters.</Empty> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Severity</th><th>Alert</th><th>User</th><th>Tool</th><th className="right">Seen</th><th>Last seen</th><th>Status</th></tr>
              </thead>
              <tbody>
                {(data?.items ?? []).map((a: any) => (
                  <tr key={a.id} className={`clickable ${id === a.id ? "selected" : ""}`} onClick={() => navigate(`/alerts/${a.id}`)}
                    tabIndex={0} onKeyDown={(e) => e.key === "Enter" && navigate(`/alerts/${a.id}`)}>
                    <td><SeverityBadge level={a.severity} /></td>
                    <td style={{ maxWidth: 420 }}>
                      <div style={{ fontWeight: 500 }}>{a.title}</div>
                      <div className="sub truncate">{a.entity_types.map(titleCase).join(", ")}</div>
                    </td>
                    <td><UserCell user={a.user} /></td>
                    <td className="secondary">{a.app?.name}</td>
                    <td className="right num">{a.occurrences}</td>
                    <td className="nowrap secondary">{ago(a.last_seen_at)}</td>
                    <td><StatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {id && (
        <Drawer title={data?.items.find((a: any) => a.id === id)?.title ?? "Alert"} sub={id} onClose={() => navigate("/alerts")}>
          <AlertDetail key={id} id={id} onChanged={reload} />
        </Drawer>
      )}
    </div>
  );
}
