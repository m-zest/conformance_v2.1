import { useState } from "react";
import { CircleCheck, Download, ShieldAlert, ShieldCheck } from "lucide-react";
import { api, useApi } from "../api";
import { Card, ErrorBox, Field, Note, PageHeader } from "../components/ui";
import { fullDateTime, num, titleCase } from "../format";

function isoDay(offsetDays: number): string {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
}

export default function Audit() {
  const ledger = useApi<any>("/audit/ledger?limit=25", 30000);
  const log = useApi<any[]>("/audit/admin-log?limit=50");
  const system = useApi<any>("/settings/system");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [from, setFrom] = useState(isoDay(-30));
  const [to, setTo] = useState(isoDay(1));
  const [format, setFormat] = useState("csv");

  const verify = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api("/audit/verify"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const exportUrl = `/api/audit/export?start=${from}T00:00:00Z&end=${to}T00:00:00Z&format=${format}`;
  const signing = system.data?.signing;

  return (
    <div className="stack">
      <PageHeader title="Audit" sub="Every interaction and every administrative action is written to a hash-chained ledger and signed, so later edits or deletions can be detected." />
      <div className="grid cols-2">
        <Card title="Ledger integrity" sub="Recomputes the full chain and checks stored records against it">
          <div className="stack-sm">
            <div className="row-wrap">
              <button className="btn primary" onClick={verify} disabled={busy}><ShieldCheck size={15} />{busy ? "Verifying" : "Verify ledger"}</button>
              {ledger.data && <span className="secondary">{num(ledger.data.total)} entries</span>}
            </div>
            <ErrorBox message={error} />
            {result?.valid && (
              <Note tone="accent" icon={<CircleCheck size={15} />}>
                <div style={{ fontWeight: 600 }}>The ledger is intact</div>
                {num(result.entries_checked)} entries verified, {num(result.records_checked)} stored records match their ledger entry.
                <div className="mono muted" style={{ marginTop: 4 }}>Head {result.head_hash.slice(0, 32)}</div>
              </Note>
            )}
            {result && !result.valid && (
              <Note tone="warn" icon={<ShieldAlert size={15} />}>
                <div style={{ fontWeight: 600 }}>Verification failed at entry #{result.failed_seq}</div>
                {titleCase(result.problem)}. Record <span className="mono">{result.record_id}</span>.
              </Note>
            )}
            {signing && (
              <dl className="kv" style={{ marginTop: 6 }}>
                <dt>Signature algorithm</dt><dd>{signing.algorithm} (ECDSA P-256)</dd>
                <dt>Signing key ID</dt><dd className="mono">{signing.key_id}</dd>
                <dt>Public key</dt><dd className="mono">{system.data.gateway_url}/.well-known/jwks.json</dd>
              </dl>
            )}
          </div>
        </Card>
        <Card title="Export records" sub="Interaction records with ledger hashes, for an audit or a regulator request">
          <div className="stack-sm">
            <div className="row-wrap" style={{ alignItems: "flex-end" }}>
              <Field label="From"><input className="input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
              <Field label="To (exclusive)"><input className="input" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
              <Field label="Format">
                <select className="select" value={format} onChange={(e) => setFormat(e.target.value)}><option value="csv">CSV</option><option value="json">JSON</option></select>
              </Field>
              <a className="btn" href={exportUrl} download><Download size={15} />Download</a>
            </div>
            <p className="hint">The export contains metadata, outcomes and hashes. It does not contain prompt text. Each export is itself recorded below.</p>
            {system.data && (
              <dl className="kv" style={{ marginTop: 6 }}>
                <dt>Retention</dt><dd>{system.data.privacy.retention_days} days, then interaction records are deleted. Ledger entries are kept.</dd>
                <dt>Prompt storage</dt><dd>{titleCase(system.data.privacy.store_prompts)}</dd>
              </dl>
            )}
          </div>
        </Card>
      </div>

      <div className="grid cols-2">
        <Card title="Latest ledger entries" flush>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th className="right">#</th><th>Time</th><th>Type</th><th>Entry hash</th></tr></thead>
              <tbody>
                {(ledger.data?.items ?? []).map((e: any) => (
                  <tr key={e.seq}>
                    <td className="right num">{e.seq}</td>
                    <td className="secondary nowrap">{fullDateTime(e.ts)}</td>
                    <td>{e.record_type === "admin" ? "Admin action" : "Interaction"}</td>
                    <td className="mono muted">{e.entry_hash.slice(0, 20)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Administrative actions" sub="Who changed what in this dashboard" flush>
          <div className="table-wrap" style={{ maxHeight: 520, overflowY: "auto" }}>
            <table className="table">
              <thead><tr><th>Time</th><th>Who</th><th>Action</th><th>Target</th></tr></thead>
              <tbody>
                {(log.data ?? []).map((a: any) => (
                  <tr key={a.id}>
                    <td className="secondary nowrap">{fullDateTime(a.ts)}</td>
                    <td>{a.actor}</td>
                    <td className="mono">{a.action}</td>
                    <td className="secondary truncate" style={{ maxWidth: 180 }}>{a.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
