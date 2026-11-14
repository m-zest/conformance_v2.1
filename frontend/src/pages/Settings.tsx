import { useState } from "react";
import { CircleCheck, CircleDashed, CircleX, Plus, Send } from "lucide-react";
import { api, useApi } from "../api";
import { useMe } from "../App";
import { Card, ErrorBox, Field, Modal, Note, PageHeader, Switch } from "../components/ui";
import { ago, fullDateTime, titleCase } from "../format";

function Detectors({ system }: { system: any }) {
  const icon = (state: string) => state === "ready" ? <CircleCheck size={15} style={{ color: "var(--good)" }} />
    : state === "disabled" ? <CircleDashed size={15} style={{ color: "var(--text-3)" }} /> : <CircleX size={15} style={{ color: "var(--critical)" }} />;
  return (
    <Card title="Detection layers" sub={`Detector set ${system.detector_set}`} flush>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Layer</th><th>Status</th><th>Details</th></tr></thead>
          <tbody>
            {system.detectors.map((d: any) => (
              <tr key={d.id}>
                <td style={{ fontWeight: 500 }}>{d.name}</td>
                <td><span className="row">{icon(d.state)}{titleCase(d.state)}</span></td>
                <td className="secondary">{d.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function AlertRules({ isAdmin }: { isAdmin: boolean }) {
  const { data: rules, reload } = useApi<any[]>("/alert-rules");
  const [error, setError] = useState<string | null>(null);
  const patch = async (id: string, body: any) => {
    setError(null);
    try {
      await api(`/alert-rules/${id}`, { method: "PATCH", body });
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Card title="Alert rules" sub="Alerts are raised for new exposure only, never for content the same user already sent" flush>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Rule</th><th>Threshold</th><th className="right">Enabled</th></tr></thead>
          <tbody>
            {(rules ?? []).map((r) => (
              <tr key={r.id}>
                <td><div style={{ fontWeight: 500 }}>{r.name}</div><div className="sub">{r.description}</div></td>
                <td className="nowrap">
                  {r.kind === "volume" ? (
                    <span className="row">
                      <input className="input num" type="number" min={2} style={{ width: 64 }} defaultValue={r.params.threshold} disabled={!isAdmin}
                        onBlur={(e) => Number(e.target.value) !== r.params.threshold && patch(r.id, { params: { threshold: Number(e.target.value) } })} aria-label="Item count" />
                      <span className="secondary">items in {r.params.window_minutes} min</span>
                    </span>
                  ) : (
                    <select className="select" value={r.params.min_severity} disabled={!isAdmin} onChange={(e) => patch(r.id, { params: { min_severity: e.target.value } })} aria-label="Minimum severity">
                      <option value="low">Low and above</option><option value="medium">Medium and above</option>
                      <option value="high">High and above</option><option value="critical">Critical only</option>
                    </select>
                  )}
                </td>
                <td className="right"><Switch checked={r.enabled} disabled={!isAdmin} label={`Enable ${r.name}`} onChange={(v) => patch(r.id, { enabled: v })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <div style={{ padding: "0 18px 12px" }}><ErrorBox message={error} /></div>}
    </Card>
  );
}

function Notifications({ system, isAdmin, reload }: { system: any; isAdmin: boolean; reload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const n = system.notifications;
  const test = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const out = await api<any>("/settings/notifications/test", { method: "POST" });
      setMessage(out.results.map((r: any) => `${titleCase(r.channel)}: ${r.status}`).join(", "));
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Notifications" sub={`Sent when an alert of ${n.min_severity} severity or above is created. Messages never contain the sensitive value or the prompt.`}
      actions={isAdmin && <button className="btn sm" onClick={test} disabled={busy}><Send size={13} />Send test</button>}>
      <div className="stack-sm">
        <div className="row-wrap">
          {n.channels.map((c: any) => (
            <span key={c.id} className={`badge ${c.configured ? "good" : ""}`}>
              {c.configured ? <CircleCheck size={12} /> : <CircleDashed size={12} />}{c.name}{c.configured ? "" : ": not configured"}
            </span>
          ))}
        </div>
        <p className="hint">Channels are configured with environment variables (SLACK_WEBHOOK_URL, TEAMS_WEBHOOK_URL, ALERT_WEBHOOK_URL, SMTP_HOST).</p>
        {message && <Note>{message}</Note>}
        {n.recent.length > 0 && (
          <div className="card">
            <div className="table-wrap" style={{ maxHeight: 220, overflowY: "auto" }}>
              <table className="table">
                <thead><tr><th>Sent</th><th>Channel</th><th>Subject</th><th>Result</th></tr></thead>
                <tbody>
                  {n.recent.map((r: any, i: number) => (
                    <tr key={i}>
                      <td className="secondary nowrap">{ago(r.ts)}</td><td>{titleCase(r.channel)}</td>
                      <td className="truncate" style={{ maxWidth: 220 }}>{r.subject}</td>
                      <td className="secondary">{r.status === "sent" ? "Delivered" : `Failed: ${r.detail}`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function Accounts() {
  const me = useMe();
  const { data: admins, reload } = useApi<any[]>("/admins");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ email: "", name: "", role: "analyst", password: "" });
  const [error, setError] = useState<string | null>(null);
  const create = async () => {
    setError(null);
    try {
      await api("/admins", { body: form });
      setAdding(false);
      setForm({ email: "", name: "", role: "analyst", password: "" });
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const patch = async (id: string, body: any) => {
    await api(`/admins/${id}`, { method: "PATCH", body }).catch((e) => setError((e as Error).message));
    reload();
  };
  return (
    <Card title="Dashboard accounts" sub="Administrators manage everything. Analysts triage alerts. Auditors have read-only access." flush
      actions={<button className="btn sm" onClick={() => setAdding(true)}><Plus size={13} />Add account</button>}>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Account</th><th>Role</th><th>Last sign-in</th><th className="right">Active</th></tr></thead>
          <tbody>
            {(admins ?? []).map((a) => (
              <tr key={a.id}>
                <td><div style={{ fontWeight: 500 }}>{a.name || a.email}</div><div className="sub">{a.email}</div></td>
                <td>
                  <select className="select" value={a.role} disabled={a.id === me.id} onChange={(e) => patch(a.id, { role: e.target.value })} aria-label="Role">
                    <option value="admin">Administrator</option><option value="analyst">Analyst</option><option value="auditor">Auditor</option>
                  </select>
                </td>
                <td className="secondary">{a.last_login_at ? fullDateTime(a.last_login_at) : "Never"}</td>
                <td className="right"><Switch checked={a.active} disabled={a.id === me.id} label="Active" onChange={(v) => patch(a.id, { active: v })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && !adding && <div style={{ padding: "0 18px 12px" }}><ErrorBox message={error} /></div>}
      {adding && (
        <Modal title="Add a dashboard account" onClose={() => setAdding(false)}
          footer={<><button className="btn" onClick={() => setAdding(false)}>Cancel</button><button className="btn primary" onClick={create}>Create account</button></>}>
          <Field label="Email"><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoFocus /></Field>
          <Field label="Name"><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Role">
            <select className="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="admin">Administrator</option><option value="analyst">Analyst</option><option value="auditor">Auditor</option>
            </select>
          </Field>
          <Field label="Initial password" hint="At least 10 characters. Ask the person to change it after the first sign-in.">
            <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
          <ErrorBox message={error} />
        </Modal>
      )}
    </Card>
  );
}

function Password() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    setError(null);
    setMessage(null);
    try {
      await api("/auth/password", { body: { current_password: current, new_password: next } });
      setMessage("Password changed. Remove ADMIN_PASSWORD from the environment or update it to match.");
      setCurrent("");
      setNext("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Card title="Your password">
      <div className="row-wrap" style={{ alignItems: "flex-end" }}>
        <Field label="Current password"><input className="input" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} /></Field>
        <Field label="New password"><input className="input" type="password" value={next} onChange={(e) => setNext(e.target.value)} /></Field>
        <button className="btn" onClick={save} disabled={!current || next.length < 10}>Change password</button>
      </div>
      <div style={{ marginTop: 8 }}><ErrorBox message={error} />{message && <Note tone="accent">{message}</Note>}</div>
    </Card>
  );
}

export default function Settings() {
  const me = useMe();
  const isAdmin = me.role === "admin";
  const { data: system, error, reload } = useApi<any>("/settings/system");
  if (error) return <ErrorBox message={error} />;
  if (!system) return null;
  return (
    <div className="stack">
      <PageHeader title="Settings" sub="Detection, alerting and access. Values marked as environment settings are changed in the deployment configuration." />
      <Detectors system={system} />
      <AlertRules isAdmin={isAdmin} />
      <Notifications system={system} isAdmin={isAdmin} reload={reload} />
      <div className="grid cols-2">
        <Card title="Privacy and retention" sub="Environment settings">
          <dl className="kv" style={{ gridTemplateColumns: "190px minmax(0, 1fr)" }}>
            <dt>Prompt storage</dt><dd>{system.privacy.store_prompts === "redacted" ? "Redacted copies only" : titleCase(system.privacy.store_prompts)}</dd>
            <dt>Response storage</dt><dd>{system.privacy.store_responses ? "Redacted copies" : "Not stored"}</dd>
            <dt>Finding previews</dt><dd>{system.privacy.store_previews ? "Short masked preview, for example the last four digits" : "Not stored"}</dd>
            <dt>Retention</dt><dd>{system.privacy.retention_days} days</dd>
          </dl>
        </Card>
        <Card title="System" sub="Environment settings">
          <dl className="kv" style={{ gridTemplateColumns: "190px minmax(0, 1fr)" }}>
            <dt>Version</dt><dd>{system.version}</dd>
            <dt>Gateway address</dt><dd className="mono">{system.gateway_url}</dd>
            <dt>OpenAI-compatible upstream</dt><dd className="mono">{system.upstreams.openai}</dd>
            <dt>Anthropic upstream</dt><dd className="mono">{system.upstreams.anthropic}</dd>
            <dt>Single sign-on for tools</dt><dd>{system.identity.oidc_enabled ? system.identity.oidc_issuer : "Not configured (gateway keys only)"}</dd>
            <dt>Compliance signing</dt><dd>{system.signing.enabled ? `${system.signing.algorithm}, token lifetime ${system.signing.ttl_seconds} s` : "Disabled"}</dd>
          </dl>
        </Card>
      </div>
      {isAdmin && <Accounts />}
      <Password />
    </div>
  );
}
