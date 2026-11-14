import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Plus } from "lucide-react";
import { api, useApi } from "../api";
import { useMe } from "../App";
import { Card, Drawer, Empty, ErrorBox, Field, Meter, ModeBadge, Modal, Note, PageHeader, RangePicker, Switch } from "../components/ui";
import { ago, money, num, pct } from "../format";

function copyText(text: string) {
  navigator.clipboard?.writeText(text).catch(() => undefined);
}

function Keys({ app, isAdmin }: { app: any; isAdmin: boolean }) {
  const { data: keys, reload } = useApi<any[]>(isAdmin ? `/apps/${app.id}/keys` : null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!isAdmin) return <Note>Only administrators can view and manage keys.</Note>;
  const create = async () => {
    setError(null);
    try {
      const result = await api<any>(`/apps/${app.id}/keys`, { body: { name, user_email: email || null } });
      setCreated(result.key);
      setName("");
      setEmail("");
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const revoke = async (id: string) => {
    await api(`/keys/${id}`, { method: "DELETE" });
    reload();
  };
  return (
    <div className="stack-sm">
      {created && (
        <Note tone="accent">
          <div style={{ fontWeight: 600 }}>Copy this key now. It is not shown again.</div>
          <div className="row" style={{ marginTop: 6 }}>
            <code className="mono" style={{ overflowWrap: "anywhere" }}>{created}</code>
            <button className="btn sm" onClick={() => copyText(created)}><Copy size={13} />Copy</button>
          </div>
        </Note>
      )}
      <div className="card">
        {keys && keys.length === 0 ? <Empty title="No keys yet" /> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Key</th><th>Identifies</th><th>Last used</th><th /></tr></thead>
              <tbody>
                {(keys ?? []).map((k) => (
                  <tr key={k.id}>
                    <td><div style={{ fontWeight: 500 }}>{k.name}</div><div className="sub mono">{k.prefix}...</div></td>
                    <td className="secondary">{k.user ?? "The application"}</td>
                    <td className="secondary nowrap">{k.revoked_at ? "Revoked" : ago(k.last_used_at)}</td>
                    <td className="right">{!k.revoked_at && <button className="btn sm danger" onClick={() => revoke(k.id)}>Revoke</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="row-wrap" style={{ alignItems: "flex-end" }}>
        <Field label="Key name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Production" /></Field>
        <Field label="Bind to one user (optional)">
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" style={{ width: 220 }} />
        </Field>
        <button className="btn" onClick={create}><Plus size={14} />Create key</button>
      </div>
      <div className="hint">An application key lets the tool assert its signed-in user. A key bound to one user is for developer tools on a personal machine.</div>
      <ErrorBox message={error} />
    </div>
  );
}

function ToolDrawer({ app, policies, gatewayUrl, onClose, onSaved }: { app: any; policies: any[]; gatewayUrl: string; onClose: () => void; onSaved: () => void }) {
  const me = useMe();
  const isAdmin = me.role === "admin";
  const [error, setError] = useState<string | null>(null);
  const patch = async (body: Record<string, unknown>) => {
    setError(null);
    try {
      await api(`/apps/${app.id}`, { method: "PATCH", body });
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const snippet = `curl ${gatewayUrl}/v1/chat/completions \\
  -H "Authorization: Bearer <gateway key>" \\
  -H "X-End-User: name@company.com" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "<model>", "messages": [{"role": "user", "content": "Hello"}]}'`;
  return (
    <Drawer title={app.name} sub={app.slug} onClose={onClose}>
      <p className="secondary">{app.description || "No description."}</p>
      <div className="section-title">Governance</div>
      <dl className="kv">
        <dt>Policy</dt>
        <dd>
          <select className="select" value={app.policy_id ?? ""} disabled={!isAdmin} onChange={(e) => patch({ policy_id: e.target.value || null })}>
            {policies.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.mode})</option>)}
          </select>
        </dd>
        <dt>Trust asserted user</dt>
        <dd className="row">
          <Switch checked={app.trust_end_user} disabled={!isAdmin} label="Trust the user the tool asserts" onChange={(v) => patch({ trust_end_user: v })} />
          <span className="secondary">Accept the X-End-User header from this tool</span>
        </dd>
        <dt>Enabled</dt>
        <dd className="row">
          <Switch checked={app.enabled} disabled={!isAdmin} label="Enabled" onChange={(v) => patch({ enabled: v })} />
          <span className="secondary">When off, the gateway rejects this tool's keys</span>
        </dd>
        <dt>Owner</dt><dd>{app.owner || <span className="muted">Not set</span>}</dd>
      </dl>
      <ErrorBox message={error} />

      <div className="section-title">Keys</div>
      <Keys app={app} isAdmin={isAdmin} />

      <div className="section-title">Connect the tool</div>
      <p className="secondary" style={{ marginBottom: 8 }}>
        Point the tool's model base URL at the gateway and replace the provider key with a gateway key. The provider key stays on the gateway.
      </p>
      <dl className="kv" style={{ marginBottom: 10 }}>
        <dt>OpenAI-compatible</dt><dd className="mono">{gatewayUrl}/v1</dd>
        <dt>Anthropic-compatible</dt><dd className="mono">{gatewayUrl}</dd>
      </dl>
      <div className="codeblock">{snippet}</div>
    </Drawer>
  );
}

function NewTool({ policies, onClose, onCreated }: { policies: any[]; onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [owner, setOwner] = useState("");
  const [policy, setPolicy] = useState(policies.find((p) => p.mode === "monitor")?.id ?? policies[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const auto = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const save = async () => {
    try {
      await api("/apps", { body: { name, slug: slug || auto, owner, policy_id: policy || null } });
      onCreated();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Modal title="Register a tool" onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save} disabled={!name}>Register</button></>}>
      <Field label="Name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus /></Field>
      <Field label="Identifier" hint="Lowercase letters, digits and hyphens.">
        <input className="input mono" value={slug} placeholder={auto} onChange={(e) => setSlug(e.target.value)} />
      </Field>
      <Field label="Owning team"><input className="input" value={owner} onChange={(e) => setOwner(e.target.value)} /></Field>
      <Field label="Policy" hint="Start in monitor mode to measure the effect before enforcing.">
        <select className="select" value={policy} onChange={(e) => setPolicy(e.target.value)}>
          {policies.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.mode})</option>)}
        </select>
      </Field>
      <ErrorBox message={error} />
    </Modal>
  );
}

export default function Tools() {
  const me = useMe();
  const [range, setRange] = useState("7d");
  const { data: apps, error, reload, loading } = useApi<any[]>(`/apps?range=${range}`);
  const policies = useApi<any>("/policies");
  const connectors = useApi<any[]>("/connectors");
  const system = useApi<any>("/settings/system");
  const [openId, setOpenId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const governed = (apps ?? []).filter((a) => a.kind === "gateway");
  const observed = (apps ?? []).filter((a) => a.kind === "connector");
  const open = governed.find((a) => a.id === openId);
  const maxRate = Math.max(10, ...governed.map((a) => (a.requests ? (a.flagged / a.requests) * 100 : 0)));

  return (
    <div className="stack">
      <PageHeader title="Tools" sub="AI tools in scope. Governed tools send their traffic through the gateway. Observed tools cannot be routed, so their vendor logs are imported instead.">
        <RangePicker value={range} onChange={setRange} />
        {me.role === "admin" && <button className="btn primary" onClick={() => setAdding(true)}><Plus size={15} />Register tool</button>}
      </PageHeader>
      <ErrorBox message={error} />
      <Card title="Governed through the gateway" sub="Inline control: requests can be logged, masked or blocked" flush className={loading ? "loading-fade" : ""}>
        {governed.length === 0 ? <Empty title="No tools registered yet">Register a tool, create a key and point the tool at the gateway.</Empty> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Tool</th><th>Policy</th><th className="right">Keys</th><th className="right">Users</th><th className="right">Interactions</th>
                  <th>Flag rate</th><th className="right">Spend</th><th className="right">30 day projection</th></tr>
              </thead>
              <tbody>
                {governed.map((a) => {
                  const rate = a.requests ? (a.flagged / a.requests) * 100 : 0;
                  return (
                    <tr key={a.id} className={`clickable ${openId === a.id ? "selected" : ""}`} onClick={() => setOpenId(a.id)}
                      tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setOpenId(a.id)}>
                      <td><div style={{ fontWeight: 500 }}>{a.name}{!a.enabled && <span className="chip" style={{ marginLeft: 8 }}>Disabled</span>}</div><div className="sub">{a.owner}</div></td>
                      <td><div className="row">{a.policy_name}<ModeBadge mode={a.policy_mode} /></div></td>
                      <td className="right num">{a.active_keys}</td>
                      <td className="right num">{a.users}</td>
                      <td className="right num">{num(a.requests)}</td>
                      <td><div className="row"><span className="num" style={{ width: 44 }}>{pct(rate)}</span><div style={{ width: 56 }}><Meter value={rate} max={maxRate} /></div></div></td>
                      <td className="right num">{money(a.cost_usd)}</td>
                      <td className="right num secondary">{money(a.cost_projection_30d)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Card title="Observed through connectors" sub="No inline control: content is analysed after the fact where the vendor makes it available" flush
        actions={<Link to="/copilot" style={{ fontSize: 13 }}>Copilot oversight</Link>}>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Tool</th><th>Connector</th><th>Last sync</th><th className="right">Users</th><th className="right">Interactions</th><th className="right">Flagged</th></tr></thead>
            <tbody>
              {observed.map((a) => {
                const c = (connectors.data ?? []).find((x) => x.id === a.id);
                return (
                  <tr key={a.id}>
                    <td><div style={{ fontWeight: 500 }}>{a.name}</div><div className="sub">{a.description}</div></td>
                    <td>{c?.mode === "live" ? <span className="badge good">Live</span> : c?.mode === "demo" ? <span className="badge outline">Demo data</span> : <span className="badge">Not connected</span>}</td>
                    <td className="secondary nowrap">{c?.last_status === "error" ? <span title={c.last_error}>Failed {ago(c.last_sync_at)}</span> : ago(c?.last_sync_at)}</td>
                    <td className="right num">{a.users}</td>
                    <td className="right num">{num(a.requests)}</td>
                    <td className="right num">{a.flagged ?? <span className="muted">No content access</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      {open && <ToolDrawer app={open} policies={policies.data?.items ?? []} gatewayUrl={system.data?.gateway_url ?? ""} onClose={() => setOpenId(null)} onSaved={reload} />}
      {adding && <NewTool policies={policies.data?.items ?? []} onClose={() => setAdding(false)} onCreated={() => { setAdding(false); reload(); }} />}
    </div>
  );
}
