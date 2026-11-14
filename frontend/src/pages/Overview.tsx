import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../api";
import { BarList, ChartCard, LineChart, Series, StackedColumns } from "../components/charts";
import { Card, Empty, ErrorBox, Meter, PageHeader, RangePicker, RiskCell, SeverityBadge, Stat, UserCell } from "../components/ui";
import { ago, bucketLabel, money, ms, num, pct, short } from "../format";

const OUTCOMES: Series[] = [
  { key: "logged", label: "Logged only", color: "var(--series-1)" },
  { key: "masked", label: "Masked", color: "var(--series-2)" },
  { key: "blocked", label: "Blocked", color: "var(--series-3)" },
];

export default function Overview() {
  const [range, setRange] = useState("7d");
  const { data, error, loading } = useApi<any>(`/overview?range=${range}`, 20000);
  const navigate = useNavigate();
  if (error && !data) return <ErrorBox message={error} />;
  if (!data) return null;
  const { kpis, deltas } = data;
  const series = data.series.map((p: any) => ({ ...p, label: bucketLabel(p.t, data.unit) }));
  const total = kpis.requests || 1;
  const governedShare = (data.coverage.governed / total) * 100;

  return (
    <div className="stack">
      <PageHeader title="Overview" sub="AI usage across the tools routed through the gateway and the tools observed from vendor logs.">
        <RangePicker value={range} onChange={setRange} />
      </PageHeader>

      <div className={`grid cols-6 ${loading ? "loading-fade" : ""}`}>
        <Stat label="Interactions" value={short(kpis.requests)} delta={deltas.requests} />
        <Stat label="Active users" value={num(kpis.active_users)} delta={deltas.active_users} />
        <Stat label="Sensitive content" value={num(kpis.flagged)} delta={deltas.flagged} upIsGood={false} />
        <Stat label="Masked" value={num(kpis.masked)} delta={deltas.masked} />
        <Stat label="Blocked" value={num(kpis.blocked)} delta={deltas.blocked} />
        <Stat label="Open alerts" value={num(kpis.open_alerts)}
          foot={<Link to="/alerts">{kpis.open_alerts_high} high or critical</Link>} />
      </div>

      <div className="grid cols-2-1">
        <ChartCard title="Interactions" sub="All tools, governed and observed" fade={loading}
          table={{ columns: ["Period", "Interactions"], rows: series.map((p: any) => [p.label, num(p.requests)]) }}>
          <LineChart name="Interactions" data={series.map((p: any) => ({ label: p.label, value: p.requests }))} />
        </ChartCard>
        <Card title="Coverage" sub="How much AI usage is under inline control">
          <div className="stack">
            <div>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span className="secondary">Governed through the gateway</span>
                <span className="num" style={{ fontWeight: 600 }}>{pct(governedShare, 0)}</span>
              </div>
              <Meter value={governedShare} />
              <div className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
                {num(data.coverage.governed)} governed in {data.coverage.governed_tools} tools, {num(data.coverage.observed)} observed
                in {data.coverage.observed_tools} tools
              </div>
            </div>
            <dl className="kv" style={{ gridTemplateColumns: "minmax(0, 1fr) max-content" }}>
              <dt>Gateway overhead, median</dt><dd className="num right">{data.latency ? ms(data.latency.p50) : "No data"}</dd>
              <dt>Gateway overhead, 95th percentile</dt><dd className="num right">{data.latency ? ms(data.latency.p95) : "No data"}</dd>
              <dt>Estimated model spend</dt><dd className="num right">{money(kpis.cost_usd)}</dd>
              <dt>Projected spend, next 30 days</dt><dd className="num right">{money(data.cost_projection_30d)}</dd>
              {kpis.would_enforce > 0 && (<><dt>Monitor mode: would have enforced</dt><dd className="num right">{num(kpis.would_enforce)}</dd></>)}
            </dl>
          </div>
        </Card>
      </div>

      <div className="grid cols-2-1">
        <ChartCard title="Interactions with sensitive content, by outcome" sub="What the policy did with each one" legend={OUTCOMES} fade={loading}
          table={{ columns: ["Period", "Logged only", "Masked", "Blocked"], rows: series.map((p: any) => [p.label, p.logged, p.masked, p.blocked]) }}>
          <StackedColumns data={series} series={OUTCOMES} />
        </ChartCard>
        <Card title="What was detected" sub="New sensitive items by category">
          <BarList items={data.categories.map((c: any) => ({ label: c.label, value: c.count }))} empty="Nothing detected in this period" />
        </Card>
      </div>

      <div className="grid cols-2">
        <Card title="People with the highest risk" sub="Score from new sensitive items, weighted by severity" flush
          actions={<Link to="/people" style={{ fontSize: 13 }}>All people</Link>}>
          {data.top_users.length === 0 ? <Empty title="No risk recorded in this period" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>User</th><th className="right">Flagged</th><th className="right">Blocked</th><th>Risk</th></tr></thead>
                <tbody>
                  {data.top_users.map((u: any) => (
                    <tr key={u.user.id} className="clickable" onClick={() => navigate(`/people/${u.user.id}`)}>
                      <td><UserCell user={u.user} /></td>
                      <td className="right num">{u.flagged}</td>
                      <td className="right num">{u.blocked}</td>
                      <td><RiskCell score={u.risk} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Tools" sub="Usage and share of interactions with new sensitive content" flush
          actions={<Link to="/tools" style={{ fontSize: 13 }}>All tools</Link>}>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Tool</th><th className="right">Interactions</th><th className="right">Users</th><th>Flag rate</th><th className="right">Spend</th></tr></thead>
              <tbody>
                {data.by_app.map((a: any) => (
                  <tr key={a.app.id}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{a.app.name}</div>
                      <div className="sub">{a.app.kind === "gateway" ? "Governed" : "Observed"}</div>
                    </td>
                    <td className="right num">{num(a.requests)}</td>
                    <td className="right num">{a.users}</td>
                    <td>
                      <div className="row"><span className="num" style={{ width: 44 }}>{pct(a.flag_rate)}</span>
                        <div style={{ width: 56 }}><Meter value={a.flag_rate} max={Math.max(10, ...data.by_app.map((x: any) => x.flag_rate))} /></div>
                      </div>
                    </td>
                    <td className="right num secondary">{a.app.kind === "gateway" ? money(a.cost_usd) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="grid cols-2">
        <Card title="Teams" sub="Where sensitive content comes from" flush>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Team</th><th className="right">Users</th><th className="right">Interactions</th><th className="right">Flagged</th><th>Flag rate</th></tr></thead>
              <tbody>
                {data.teams.map((t: any) => (
                  <tr key={t.team}>
                    <td style={{ fontWeight: 500 }}>{t.team}</td>
                    <td className="right num">{t.users}</td>
                    <td className="right num">{num(t.requests)}</td>
                    <td className="right num">{t.flagged}</td>
                    <td>
                      <div className="row"><span className="num" style={{ width: 44 }}>{pct(t.flag_rate)}</span>
                        <div style={{ width: 56 }}><Meter value={t.flag_rate} max={Math.max(10, ...data.teams.map((x: any) => x.flag_rate))} /></div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Alerts that need attention" flush actions={<Link to="/alerts" style={{ fontSize: 13 }}>Alert inbox</Link>}>
          {data.recent_alerts.length === 0 ? <Empty title="No open alerts" /> : (
            <div className="table-wrap">
              <table className="table">
                <tbody>
                  {data.recent_alerts.map((a: any) => (
                    <tr key={a.id} className="clickable" onClick={() => navigate(`/alerts/${a.id}`)}>
                      <td style={{ width: 1 }}><SeverityBadge level={a.severity} /></td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{a.title}</div>
                        <div className="sub">{a.user?.name ?? "Unknown user"}, {a.app?.name ?? "unknown tool"}</div>
                      </td>
                      <td className="right nowrap muted" style={{ fontSize: 12.5 }}>{ago(a.last_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
