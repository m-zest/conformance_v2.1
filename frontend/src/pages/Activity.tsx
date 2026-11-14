import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api, query, useApi } from "../api";
import { InteractionsTable, RequestDrawer } from "../components/detail";
import { Card, Empty, ErrorBox, PageHeader, RangePicker } from "../components/ui";
import { num } from "../format";

export default function Activity() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("id");
  const [range, setRange] = useState(selected ? "30d" : "24h");
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [appId, setAppId] = useState("");
  const [action, setAction] = useState("");
  const [category, setCategory] = useState("");
  const [flagged, setFlagged] = useState(false);
  const [extra, setExtra] = useState<any[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const meta = useApi<any>("/meta");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(q), 250);
    return () => window.clearTimeout(timer);
  }, [q]);

  const base = { range, q: debounced, app_id: appId, action, category, flagged, limit: 50 };
  const path = `/activity${query(base)}`;
  const { data, error, loading } = useApi<any>(path, 15000);

  useEffect(() => {
    setExtra([]);
    setCursor(null);
  }, [path]);

  const items = [...(data?.items ?? []), ...extra];
  const next = cursor ?? data?.next_cursor;
  const more = async () => {
    const page = await api<any>(`/activity${query({ ...base, cursor: next })}`);
    setExtra([...extra, ...page.items]);
    setCursor(page.next_cursor ?? "");
  };
  const open = (id: string | null) => {
    const copy = new URLSearchParams(params);
    if (id) copy.set("id", id); else copy.delete("id");
    setParams(copy, { replace: true });
  };

  return (
    <div>
      <PageHeader title="Activity" sub="Every interaction the gateway handled or a connector observed. Prompts are stored in redacted form only.">
        <RangePicker value={range} onChange={setRange} />
      </PageHeader>
      <div className="filters">
        <div className="search"><Search size={15} />
          <input className="input" placeholder="Search user, team or model" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        </div>
        <select className="select" value={appId} onChange={(e) => setAppId(e.target.value)} aria-label="Tool">
          <option value="">All tools</option>
          {(meta.data?.apps ?? []).map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select className="select" value={action} onChange={(e) => setAction(e.target.value)} aria-label="Outcome">
          <option value="">Any outcome</option>
          <option value="allowed">Allowed</option>
          <option value="masked">Masked</option>
          <option value="blocked">Blocked</option>
          <option value="observed">Observed</option>
          <option value="would_enforce">Monitor mode: would enforce</option>
        </select>
        <select className="select" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">Any category</option>
          {(meta.data?.categories ?? []).map((c: any) => <option key={c.id} value={c.id}>{c.label}</option>)}
        </select>
        <label className="row" style={{ fontSize: 13 }}>
          <input type="checkbox" checked={flagged} onChange={(e) => setFlagged(e.target.checked)} />
          Only with detected content
        </label>
        {data && <span className="muted" style={{ marginLeft: "auto", fontSize: 13 }}>{num(data.total)} interactions</span>}
      </div>
      <ErrorBox message={error} />
      <Card flush className={loading && !data ? "loading-fade" : ""}>
        {data && items.length === 0 ? <Empty title="No interactions match">Try a longer time range or fewer filters.</Empty> : (
          <InteractionsTable items={items} onOpen={open} selected={selected} />
        )}
        {next && (
          <div className="card-foot" style={{ textAlign: "center" }}>
            <button className="btn" onClick={more}>Load more</button>
          </div>
        )}
      </Card>
      {selected && <RequestDrawer id={selected} onClose={() => open(null)} />}
    </div>
  );
}
