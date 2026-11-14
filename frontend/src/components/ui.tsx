import { ReactNode, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  AlertOctagon, AlertTriangle, ArrowDownRight, ArrowUpRight, Ban, Check, CircleAlert, CircleCheck, Eye, EyeOff, Info,
  ScanSearch, X,
} from "lucide-react";
import { initials, titleCase } from "../format";

export const RANGES: [string, string][] = [["24h", "24 hours"], ["7d", "7 days"], ["14d", "14 days"], ["30d", "30 days"]];

export function PageHeader(props: { title: string; sub?: ReactNode; children?: ReactNode; crumb?: ReactNode }) {
  return (
    <div>
      {props.crumb}
      <div className="page-head">
        <div>
          <h1 className="page-title">{props.title}</h1>
          {props.sub && <p className="page-sub">{props.sub}</p>}
        </div>
        {props.children && <div className="page-actions">{props.children}</div>}
      </div>
    </div>
  );
}

export function Segmented<T extends string>(props: { value: T; options: [T, string][]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="group" aria-label={props.label}>
      {props.options.map(([value, label]) => (
        <button key={value} type="button" aria-pressed={props.value === value} onClick={() => props.onChange(value)}>
          {label}
        </button>
      ))}
    </div>
  );
}

export function RangePicker(props: { value: string; onChange: (v: string) => void }) {
  return <Segmented label="Time range" value={props.value} options={RANGES} onChange={props.onChange} />;
}

export function Card(props: { title?: ReactNode; sub?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean; className?: string }) {
  return (
    <section className={`card ${props.className ?? ""}`}>
      {(props.title || props.actions) && (
        <div className="card-head">
          <div className="grow">
            {props.title && <h2 className="card-title">{props.title}</h2>}
            {props.sub && <div className="card-sub">{props.sub}</div>}
          </div>
          {props.actions}
        </div>
      )}
      <div className={`card-body ${props.flush ? "flush" : ""}`}>{props.children}</div>
    </section>
  );
}

export function Stat(props: { label: string; value: ReactNode; delta?: number | null; upIsGood?: boolean; foot?: ReactNode; icon?: ReactNode }) {
  const { delta } = props;
  let deltaNode: ReactNode = null;
  if (delta != null) {
    const up = delta > 0;
    const tone = delta === 0 || props.upIsGood === undefined ? "" : up === props.upIsGood ? "good" : "bad";
    deltaNode = (
      <span className={`delta ${tone}`}>
        {delta !== 0 && (up ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />)}
        {Math.abs(delta).toFixed(1)}%
      </span>
    );
  }
  return (
    <div className="card stat">
      <div className="stat-label">{props.icon}{props.label}</div>
      <div className="stat-value">{props.value}</div>
      <div className="stat-foot">
        {deltaNode}
        {props.foot ?? (deltaNode && <span>vs prior period</span>)}
      </div>
    </div>
  );
}

const SEVERITY_ICON: Record<string, ReactNode> = {
  critical: <AlertOctagon size={12} />, high: <AlertTriangle size={12} />, medium: <CircleAlert size={12} />,
  low: <Info size={12} />, info: <Info size={12} />,
};

export function SeverityBadge({ level }: { level: string }) {
  return <span className={`badge ${level}`}>{SEVERITY_ICON[level] ?? SEVERITY_ICON.info}{titleCase(level)}</span>;
}

export function ActionBadge({ action, would }: { action: string; would?: string | null }) {
  if (action === "blocked") return <span className="badge high"><Ban size={12} />Blocked</span>;
  if (action === "masked") return <span className="badge accent"><EyeOff size={12} />Masked</span>;
  if (action === "observed") return <span className="badge"><Eye size={12} />Observed</span>;
  if (action === "error") return <span className="badge critical"><X size={12} />Error</span>;
  if (would) return <span className="badge outline"><ScanSearch size={12} />Would {would}</span>;
  return <span className="badge"><Check size={12} />Allowed</span>;
}

const STATUS_LABEL: Record<string, string> = {
  open: "Open", acknowledged: "Acknowledged", resolved: "Resolved", false_positive: "False positive",
};

export function StatusBadge({ status }: { status: string }) {
  if (status === "resolved") return <span className="badge good"><CircleCheck size={12} />Resolved</span>;
  if (status === "open") return <span className="badge medium"><CircleAlert size={12} />Open</span>;
  return <span className="badge">{STATUS_LABEL[status] ?? titleCase(status)}</span>;
}

export function ModeBadge({ mode }: { mode: string | null | undefined }) {
  if (mode === "enforce") return <span className="badge accent">Enforce</span>;
  if (mode === "monitor") return <span className="badge outline">Monitor</span>;
  return <span className="badge">Observed</span>;
}

export function Avatar({ name, large }: { name?: string | null; large?: boolean }) {
  return <span className={`avatar ${large ? "lg" : ""}`} aria-hidden>{initials(name)}</span>;
}

export function UserCell({ user, link = true }: { user: any; link?: boolean }) {
  if (!user) return <span className="muted">Unknown</span>;
  const name = link && !user.unattributed
    ? <Link className="name" to={`/people/${user.id}`} onClick={(e) => e.stopPropagation()}>{user.name}</Link>
    : <span className="name">{user.name}</span>;
  return (
    <div className="cell-user">
      <Avatar name={user.unattributed ? "?" : user.name} />
      <div className="grow truncate">
        {name}
        {user.team && <div className="sub truncate">{user.team}</div>}
      </div>
    </div>
  );
}

export function Meter({ value, max = 100, neutral }: { value: number; max?: number; neutral?: boolean }) {
  const width = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return <div className={`meter ${neutral ? "neutral" : ""}`}><span style={{ width: `${width}%` }} /></div>;
}

export function RiskCell({ score }: { score: number }) {
  return (
    <div className="row" title="Risk score from 0 to 100, based on new sensitive items weighted by severity">
      <span className="num" style={{ width: 24, textAlign: "right", fontWeight: 550 }}>{score}</span>
      <div style={{ width: 64 }}><Meter value={score} /></div>
    </div>
  );
}

export function Switch(props: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button type="button" role="switch" className="switch" aria-checked={props.checked} aria-label={props.label}
      disabled={props.disabled} onClick={() => props.onChange(!props.checked)} />
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><strong>{title}</strong>{children}</div>;
}

export function ErrorBox({ message }: { message: string | null }) {
  return message ? <div className="error-box" role="alert">{message}</div> : null;
}

export function Note({ children, tone, icon }: { children: ReactNode; tone?: "accent" | "warn"; icon?: ReactNode }) {
  return <div className={`note ${tone ?? ""}`}>{icon ?? <Info size={15} />}<div>{children}</div></div>;
}

function useEscape(onClose: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);
}

export function Drawer(props: { title: ReactNode; sub?: ReactNode; onClose: () => void; children: ReactNode }) {
  useEscape(props.onClose);
  return (
    <>
      <div className="scrim" onClick={props.onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-head">
          <div className="grow">
            <div style={{ fontWeight: 600, fontSize: 15 }}>{props.title}</div>
            {props.sub && <div className="muted" style={{ fontSize: 12.5 }}>{props.sub}</div>}
          </div>
          <button className="btn ghost icon" onClick={props.onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <div className="drawer-body">{props.children}</div>
      </aside>
    </>
  );
}

export function Modal(props: { title: string; onClose: () => void; children: ReactNode; footer: ReactNode }) {
  useEscape(props.onClose);
  return (
    <>
      <div className="scrim" onClick={props.onClose} />
      <div className="modal" role="dialog" aria-modal="true" aria-label={props.title}>
        <div className="modal-head">{props.title}</div>
        <div className="modal-body">{props.children}</div>
        <div className="modal-foot">{props.footer}</div>
      </div>
    </>
  );
}

export function Field(props: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="label">{props.label}</span>
      {props.children}
      {props.hint && <span className="hint">{props.hint}</span>}
    </label>
  );
}

export function SourceLabel({ source }: { source: string }) {
  const label = source === "gateway" ? "Gateway" : source === "m365_copilot" ? "Microsoft 365 Copilot" : source === "github_copilot" ? "GitHub Copilot" : source;
  return <span className="chip">{label}</span>;
}
