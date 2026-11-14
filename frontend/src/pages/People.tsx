import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Search } from "lucide-react";
import { query, useApi } from "../api";
import { BarList, ChartCard, LineChart } from "../components/charts";
import { InteractionsTable, RequestDrawer } from "../components/detail";
import { Avatar, Card, Empty, ErrorBox, PageHeader, RangePicker, RiskCell, SeverityBadge, Stat, StatusBadge, UserCell } from "../components/ui";
import { ago, bucketLabel, num, titleCase } from "../format";

export function People() {
  const navigate = useNavigate();
  const [range, setRange] = useState("7d");
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [team, setTeam] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(q), 250);
    return () => window.clearTimeout(timer);
  }, [q]);
  const { data, error, loading } = useApi<any>(`/users${query({ range, q: debounced, team })}`);

  return (
    <div>
      <PageHeader title="People" sub="Everyone who used an AI tool, ranked by risk. The score counts new sensitive items weighted by severity, on a scale of 0 to 100.">
        <RangePicker value={range} onChange={setRange} />
      </PageHeader>
      <div className="filters">
        <div className="search"><Search size={15} />
          <input className="input" placeholder="Search name, email or team" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        </div>
        <select className="select" value={team} onChange={(e) => setTeam(e.target.value)} aria-label="Team">
          <option value="">All teams</option>
          {(data?.teams ?? []).map((t: string) => <option key={t}>{t}</option>)}
        </select>
        {data && <span className="muted" style={{ marginLeft: "auto", fontSize: 13 }}>{data.items.length} people</span>}
      </div>
      <ErrorBox message={error} />
      <Card flush className={loading ? "loading-fade" : ""}>
        {data && data.items.length === 0 ? <Empty title="Nobody matches" /> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>User</th><th className="right">Interactions</th><th className="right">Flagged</th><th className="right">Masked</th>
                  <th className="right">Blocked</th><th>Risk</th><th>Last active</th></tr>
              </thead>
              <tbody>
                {(data?.items ?? []).map((u: any) => (
                  <tr key={u.id} className="clickable" onClick={() => navigate(`/people/${u.id}`)}
                    tabIndex={0} onKeyDown={(e) => e.key === "Enter" && navigate(`/people/${u.id}`)}>
                    <td><UserCell user={u} link={false} /></td>
                    <td className="right num">{num(u.requests)}</td>
                    <td className="right num">{u.flagged}</td>
                    <td className="right num">{u.masked}</td>
                    <td className="right num">{u.blocked}</td>
                    <td><RiskCell score={u.risk} /></td>
                    <td className="nowrap secondary">{ago(u.last)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

export function Person() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [range, setRange] = useState("14d");
  const [open, setOpen] = useState<string | null>(null);
  const { data: user, error, loading } = useApi<any>(`/users/${id}?range=${range}`);
  if (error) return <ErrorBox message={error} />;
  if (!user) return null;
  const unit = range === "24h" ? "hour" : "day";
  const series = user.series.map((p: any) => ({ label: bucketLabel(p.t, unit), value: p.requests, flagged: p.flagged }));
  const stats = user.stats ?? { requests: 0, flagged: 0, masked: 0, blocked: 0, risk: 0 };

  return (
    <div className="stack">
      <div>
        <Link to="/people" className="crumb"><ChevronLeft size={14} />People</Link>
        <div className="page-head">
          <Avatar name={user.name} large />
          <div>
            <h1 className="page-title">{user.name}</h1>
            <p className="page-sub">{[user.title, user.team, user.email].filter(Boolean).join(" · ")}</p>
          </div>
          <div className="page-actions"><RangePicker value={range} onChange={setRange} /></div>
        </div>
      </div>

      <div className={`grid cols-4 ${loading ? "loading-fade" : ""}`}>
        <Stat label="Interactions" value={num(stats.requests)} />
        <Stat label="Sensitive content" value={num(stats.flagged)} />
        <Stat label="Masked or blocked" value={num(stats.masked + stats.blocked)} />
        <Stat label="Risk score" value={stats.risk} foot={<span>0 to 100, this period</span>} />
      </div>

      <div className="grid cols-2-1">
        <ChartCard title="Interactions" sub="All tools" fade={loading}
          table={{ columns: ["Period", "Interactions", "Flagged"], rows: series.map((p: any) => [p.label, p.value, p.flagged]) }}>
          <LineChart name="Interactions" data={series} height={200} />
        </ChartCard>
        <Card title="What was detected" sub="New sensitive items by type">
          <BarList items={user.findings.slice(0, 8).map((f: any) => ({ label: titleCase(f.entity_label), value: f.count }))}
            empty="Nothing detected in this period" />
        </Card>
      </div>

      <div className="grid cols-2">
        <Card title="Tools used" flush>
          {user.apps.length === 0 ? <Empty title="No activity in this period" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Tool</th><th className="right">Interactions</th><th className="right">Flagged</th><th>Last used</th></tr></thead>
                <tbody>
                  {user.apps.map((a: any) => (
                    <tr key={a.app.id}>
                      <td style={{ fontWeight: 500 }}>{a.app.name}</td>
                      <td className="right num">{num(a.requests)}</td>
                      <td className="right num">{a.flagged}</td>
                      <td className="secondary nowrap">{ago(a.last)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Alerts" flush>
          {user.alerts.length === 0 ? <Empty title="No alerts for this person" /> : (
            <div className="table-wrap">
              <table className="table">
                <tbody>
                  {user.alerts.map((a: any) => (
                    <tr key={a.id} className="clickable" onClick={() => navigate(`/alerts/${a.id}`)}>
                      <td style={{ width: 1 }}><SeverityBadge level={a.severity} /></td>
                      <td><div style={{ fontWeight: 500 }}>{a.title}</div><div className="sub">{a.app?.name}</div></td>
                      <td><StatusBadge status={a.status} /></td>
                      <td className="right nowrap muted" style={{ fontSize: 12.5 }}>{ago(a.last_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card title="Recent interactions with detected content" flush>
        {user.recent.length === 0 ? <Empty title="Nothing detected in this period" /> : (
          <InteractionsTable items={user.recent} onOpen={setOpen} selected={open} showUser={false} />
        )}
      </Card>
      {open && <RequestDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

export default People;
