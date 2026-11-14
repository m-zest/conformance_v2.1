import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api, useApi } from "../api";
import { useMe } from "../App";
import { FindingsTable, RedactedText } from "../components/detail";
import { ActionBadge, Card, Drawer, ErrorBox, Field, ModeBadge, Note, PageHeader, Segmented } from "../components/ui";
import { ago } from "../format";

const ACTIONS: [string, string][] = [["allow", "Ignore"], ["log", "Log"], ["mask", "Mask"], ["block", "Block"]];
const HELP: Record<string, string> = {
  "secret.credential": "Cloud keys, access tokens, private keys, connection strings, passwords",
  "pii.financial": "Payment card numbers and IBANs, validated by checksum",
  "pii.identity": "National IDs, tax codes, passport numbers, dates of birth",
  "pii.health": "Medical record numbers and patient identifiers",
  "pii.contact": "Email addresses, phone numbers, public IP addresses",
  "pii.person": "Names of people and places, found by the named entity model",
  confidential: "Confidentiality markings and the custom terms defined below",
  injection: "Attempts to override instructions or extract hidden configuration",
  content_safety: "Requests the guard model classifies as unsafe",
};

function Editor({ policy, categories, onClose, onSaved }: { policy: any | null; categories: any[]; onClose: () => void; onSaved: () => void }) {
  const me = useMe();
  const isAdmin = me.role === "admin";
  const [draft, setDraft] = useState<any>(() => policy
    ? JSON.parse(JSON.stringify(policy))
    : { name: "", description: "", mode: "monitor", rules: Object.fromEntries(categories.map((c) => [c.id, "log"])), custom_terms: [] });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (patch: any) => setDraft({ ...draft, ...patch });
  const setTerm = (i: number, patch: any) => set({ custom_terms: draft.custom_terms.map((t: any, n: number) => (n === i ? { ...t, ...patch } : t)) });
  const save = async () => {
    setBusy(true);
    setError(null);
    const body = { name: draft.name, description: draft.description, mode: draft.mode, rules: draft.rules, custom_terms: draft.custom_terms };
    try {
      if (policy) await api(`/policies/${policy.id}`, { method: "PUT", body });
      else await api("/policies", { body });
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Drawer title={policy ? policy.name : "New policy"} sub={policy ? `Version ${policy.version}` : undefined} onClose={onClose}>
      <div className="stack">
        <Field label="Name"><input className="input" value={draft.name} disabled={!isAdmin} onChange={(e) => set({ name: e.target.value })} /></Field>
        <Field label="Description"><textarea className="textarea" rows={2} value={draft.description} disabled={!isAdmin} onChange={(e) => set({ description: e.target.value })} /></Field>
        <div className="field">
          <span className="label">Mode</span>
          <div className="row-wrap">
            <Segmented label="Mode" value={draft.mode} options={[["monitor", "Monitor"], ["enforce", "Enforce"]]} onChange={(mode) => isAdmin && set({ mode })} />
            <span className="hint">{draft.mode === "monitor"
              ? "Nothing is changed or blocked. The dashboard shows what enforcement would have done."
              : "Mask and block rules are applied before the request leaves the gateway."}</span>
          </div>
        </div>
      </div>

      <div className="section-title">Rules by category</div>
      <div className="rule-grid">
        {categories.map((c) => (
          <div key={c.id} style={{ display: "contents" }}>
            <div>
              <div style={{ fontWeight: 500 }}>{c.label}</div>
              <div className="hint">{HELP[c.id]}</div>
            </div>
            <Segmented label={c.label} value={draft.rules[c.id] ?? "log"}
              options={ACTIONS.filter(([a]) => c.maskable || a !== "mask")}
              onChange={(action) => isAdmin && set({ rules: { ...draft.rules, [c.id]: action } })} />
          </div>
        ))}
      </div>

      <div className="section-title">Custom terms</div>
      <p className="hint" style={{ marginBottom: 8 }}>Project code names, customer identifiers or any pattern specific to your company. Matches fall under Confidential business data.</p>
      <div className="stack-sm">
        {draft.custom_terms.map((t: any, i: number) => (
          <div className="row" key={i}>
            <input className="input" style={{ width: 150 }} placeholder="Label" value={t.label ?? ""} disabled={!isAdmin} onChange={(e) => setTerm(i, { label: e.target.value })} aria-label="Label" />
            <input className="input grow mono" placeholder="Keyword or pattern" value={t.pattern ?? ""} disabled={!isAdmin} onChange={(e) => setTerm(i, { pattern: e.target.value })} aria-label="Pattern" />
            <select className="select" value={t.type ?? "keyword"} disabled={!isAdmin} onChange={(e) => setTerm(i, { type: e.target.value })} aria-label="Type">
              <option value="keyword">Keyword</option><option value="regex">Regular expression</option>
            </select>
            <select className="select" value={t.severity ?? "medium"} disabled={!isAdmin} onChange={(e) => setTerm(i, { severity: e.target.value })} aria-label="Severity">
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
            </select>
            {isAdmin && <button className="btn ghost icon" aria-label="Remove term" onClick={() => set({ custom_terms: draft.custom_terms.filter((_: any, n: number) => n !== i) })}><Trash2 size={15} /></button>}
          </div>
        ))}
        {isAdmin && (
          <div><button className="btn sm" onClick={() => set({ custom_terms: [...draft.custom_terms, { label: "", pattern: "", type: "keyword", severity: "medium" }] })}><Plus size={13} />Add term</button></div>
        )}
      </div>

      <div className="divider" />
      <ErrorBox message={error} />
      {isAdmin ? (
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={busy || !draft.name}>{policy ? "Save as new version" : "Create policy"}</button>
        </div>
      ) : <Note>Only administrators can change policies.</Note>}
    </Drawer>
  );
}

function TestBench({ policies }: { policies: any[] }) {
  const [text, setText] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async () => {
    setError(null);
    try {
      setResult(await api("/policies/test", { body: { text, policy_id: policyId || null } }));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Card title="Test a prompt" sub="See what the detectors find and what a policy would do. Nothing typed here is stored.">
      <div className="stack-sm">
        <textarea className="textarea" rows={4} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Paste a prompt, for example: Refund card 4539 1488 0343 6467 for anna@example.org" />
        <div className="row-wrap">
          <select className="select" value={policyId} onChange={(e) => setPolicyId(e.target.value)} aria-label="Policy">
            <option value="">Default policy</option>
            {policies.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button className="btn primary" onClick={run} disabled={!text.trim()}>Run test</button>
        </div>
        <ErrorBox message={error} />
        {result && (
          <div className="stack-sm" style={{ marginTop: 6 }}>
            <div className="row-wrap">
              <span className="secondary">Result under {result.policy}:</span>
              <ActionBadge action={result.enforced === "block" ? "blocked" : result.enforced === "mask" ? "masked" : "allowed"}
                would={result.enforced === "allow" && result.would !== "allow" ? result.would : null} />
              <ModeBadge mode={result.mode} />
            </div>
            <div className="card"><FindingsTable findings={result.findings} /></div>
            {result.forwarded != null && (
              <>
                <div className="label">What the model provider would receive</div>
                <RedactedText text={result.forwarded} />
              </>
            )}
            <div className="label">What would be stored</div>
            <RedactedText text={result.redacted} />
          </div>
        )}
      </div>
    </Card>
  );
}

export default function Policies() {
  const me = useMe();
  const { data, error, reload } = useApi<any>("/policies");
  const [editing, setEditing] = useState<any | "new" | null>(null);
  const items = data?.items ?? [];
  return (
    <div className="stack">
      <PageHeader title="Policies" sub="A policy decides what happens to each category of sensitive content. Assign policies to tools on the Tools page.">
        {me.role === "admin" && <button className="btn primary" onClick={() => setEditing("new")}><Plus size={15} />New policy</button>}
      </PageHeader>
      <ErrorBox message={error} />
      <Card flush>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Policy</th><th>Mode</th><th>Masks</th><th>Blocks</th><th>Used by</th><th>Last changed</th></tr></thead>
            <tbody>
              {items.map((p: any) => {
                const labels = (action: string) => (data.categories as any[]).filter((c) => p.rules[c.id] === action).map((c) => c.label).join(", ");
                return (
                  <tr key={p.id} className="clickable" onClick={() => setEditing(p)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setEditing(p)}>
                    <td style={{ maxWidth: 320 }}>
                      <div style={{ fontWeight: 500 }}>{p.name}{p.is_default && <span className="chip" style={{ marginLeft: 8 }}>Default</span>}</div>
                      <div className="sub">{p.description}</div>
                    </td>
                    <td><ModeBadge mode={p.mode} /></td>
                    <td className="secondary" style={{ maxWidth: 200 }}>{labels("mask") || "Nothing"}</td>
                    <td className="secondary" style={{ maxWidth: 200 }}>{labels("block") || "Nothing"}</td>
                    <td className="secondary">{p.tools.length ? p.tools.join(", ") : "No tools"}</td>
                    <td className="secondary nowrap">v{p.version}, {ago(p.updated_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      <TestBench policies={items} />
      {editing && (
        <Editor policy={editing === "new" ? null : editing} categories={data.categories} onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }} />
      )}
    </div>
  );
}
