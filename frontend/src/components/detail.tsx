import { Fragment, ReactNode } from "react";
import { Link } from "react-router-dom";
import { FileCheck2, ShieldCheck } from "lucide-react";
import { useApi } from "../api";
import { fullDateTime, money, ms, num, titleCase } from "../format";
import { ActionBadge, Drawer, Empty, ErrorBox, ModeBadge, Note, SeverityBadge, SourceLabel, UserCell } from "./ui";

/** Renders stored text and highlights the placeholders that replaced sensitive values. */
export function RedactedText({ text }: { text: string | null | undefined }) {
  if (!text) return <div className="codeblock muted">Content is not stored for this interaction.</div>;
  const parts = text.split(/(\[[A-Z][A-Z0-9_]*_\d+\])/g);
  return (
    <div className="codeblock">
      {parts.map((part, i) => (/^\[[A-Z][A-Z0-9_]*_\d+\]$/.test(part) ? <mark key={i}>{part}</mark> : <Fragment key={i}>{part}</Fragment>))}
    </div>
  );
}

const ACTION_TEXT: Record<string, string> = { log: "Logged", mask: "Masked", block: "Blocked", allow: "Ignored" };

export function FindingsTable({ findings }: { findings: any[] }) {
  if (!findings?.length) return <Empty title="No sensitive content detected" />;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr><th>Item</th><th>Category</th><th>Severity</th><th>Rule action</th><th>Detector</th><th className="right">Confidence</th></tr>
        </thead>
        <tbody>
          {findings.map((f) => (
            <tr key={f.id ?? `${f.entity_type}-${f.start}`}>
              <td>
                <div style={{ fontWeight: 500 }}>{titleCase(f.entity_label)}</div>
                <div className="sub">
                  {f.preview && <span className="mono">{f.preview}</span>}
                  {f.direction === "response" && <span> in the model response</span>}
                  {f.is_new === false && <span> (seen before from this user)</span>}
                </div>
              </td>
              <td className="secondary">{f.category_label}</td>
              <td><SeverityBadge level={f.severity} /></td>
              <td>{ACTION_TEXT[f.action] ?? f.action}</td>
              <td className="secondary">{f.detector}</td>
              <td className="right num">{Math.round(f.confidence * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function outcomeNote(r: any): ReactNode {
  if (r.action === "blocked") return <Note tone="warn">The request was blocked and never reached the model provider.</Note>;
  if (r.action === "masked") return <Note tone="accent">Sensitive values were replaced with placeholders before the request was forwarded.</Note>;
  if (r.action === "observed") return <Note>This interaction was read from vendor logs after it happened. It could not be modified or blocked.</Note>;
  if (r.would_action) return <Note>The policy is in monitor mode, so the request was forwarded unchanged. In enforce mode it would have been {r.would_action === "block" ? "blocked" : "masked"}.</Note>;
  return null;
}

export function RequestDetail({ id }: { id: string }) {
  const { data: r, error } = useApi<any>(`/activity/${id}`);
  if (error) return <ErrorBox message={error} />;
  if (!r) return null;
  return (
    <div>
      <div className="row-wrap" style={{ marginBottom: 14 }}>
        <ActionBadge action={r.action} would={r.would_action} />
        {r.finding_count > 0 && <SeverityBadge level={r.severity} />}
        <SourceLabel source={r.source} />
        <span className="muted" style={{ fontSize: 12.5 }}>{fullDateTime(r.ts)}</span>
      </div>
      {outcomeNote(r)}

      <div className="section-title">Context</div>
      <dl className="kv">
        <dt>User</dt><dd><UserCell user={r.user} /></dd>
        <dt>Tool</dt><dd>{r.app?.name ?? "Unknown"}{r.host_app ? `, ${r.host_app}` : ""}</dd>
        {r.model && <><dt>Model</dt><dd className="mono">{r.model}</dd></>}
        <dt>Policy mode</dt><dd><ModeBadge mode={r.source === "gateway" ? r.mode : null} /></dd>
        {r.source === "gateway" && r.action !== "blocked" && (
          <>
            <dt>Tokens</dt><dd className="num">{num(r.input_tokens)} in, {num(r.output_tokens)} out{r.usage_estimated ? " (estimated)" : ""}</dd>
            <dt>Estimated cost</dt><dd className="num">{money(r.cost_usd)}</dd>
            <dt>Latency</dt><dd className="num">{ms(r.latency_ms)} total, {ms(r.overhead_ms)} added by the gateway</dd>
          </>
        )}
        {r.error && <><dt>Note</dt><dd>{r.error}</dd></>}
      </dl>

      <div className="section-title">Detected content</div>
      <div className="card"><FindingsTable findings={r.findings} /></div>

      <div className="section-title">Prompt as stored (redacted)</div>
      <RedactedText text={r.prompt_text} />
      {r.response_text && (
        <>
          <div className="section-title">Response as stored (redacted)</div>
          <RedactedText text={r.response_text} />
        </>
      )}

      <div className="section-title">Integrity</div>
      <dl className="kv">
        <dt>Record ID</dt><dd className="mono">{r.id}</dd>
        {r.ledger && <><dt>Ledger entry</dt><dd><span className="row"><FileCheck2 size={14} />#{r.ledger.seq} <span className="mono muted truncate">{r.ledger.entry_hash.slice(0, 24)}</span></span></dd></>}
        {r.prompt_sha256 && <><dt>Body SHA-256</dt><dd className="mono muted">{r.prompt_sha256.slice(0, 32)}</dd></>}
        {r.compliance_token && <><dt>Compliance token</dt><dd><span className="row"><ShieldCheck size={14} />Signed and attached to the forwarded request</span></dd></>}
      </dl>

      {r.alerts?.length > 0 && (
        <>
          <div className="section-title">Related alerts</div>
          <div className="stack-sm">
            {r.alerts.map((a: any) => (
              <Link key={a.id} to={`/alerts/${a.id}`} className="row"><SeverityBadge level={a.severity} />{a.title}</Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function RequestDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  return <Drawer title="Interaction" sub={id} onClose={onClose}><RequestDetail id={id} /></Drawer>;
}

/** Shared table of interactions used on several pages. */
export function InteractionsTable(props: { items: any[]; onOpen: (id: string) => void; selected?: string | null; showUser?: boolean; showTool?: boolean }) {
  const showUser = props.showUser ?? true;
  const showTool = props.showTool ?? true;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            {showUser && <th>User</th>}
            {showTool && <th>Tool</th>}
            <th>Outcome</th>
            <th>Detected</th>
            <th className="right">Tokens</th>
          </tr>
        </thead>
        <tbody>
          {props.items.map((r) => (
            <tr key={r.id} className={`clickable ${props.selected === r.id ? "selected" : ""}`} onClick={() => props.onOpen(r.id)}
              tabIndex={0} onKeyDown={(e) => e.key === "Enter" && props.onOpen(r.id)}>
              <td className="nowrap secondary">{fullDateTime(r.ts).replace(/,\s*\d{4}/, "")}</td>
              {showUser && <td><UserCell user={r.user} /></td>}
              {showTool && (
                <td>
                  <div>{r.app?.name ?? "Unknown"}</div>
                  <div className="sub">{r.host_app ?? r.model}</div>
                </td>
              )}
              <td><ActionBadge action={r.action} would={r.would_action} /></td>
              <td>
                {r.finding_count > 0 ? (
                  <div className="row-wrap">
                    <SeverityBadge level={r.severity} />
                    <span className="secondary">{r.finding_count} {r.finding_count === 1 ? "item" : "items"}</span>
                  </div>
                ) : <span className="muted">Nothing</span>}
              </td>
              <td className="right num secondary">{r.action === "blocked" || r.source !== "gateway" ? "" : num(r.input_tokens + r.output_tokens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
