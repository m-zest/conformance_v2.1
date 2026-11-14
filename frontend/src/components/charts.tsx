import { ReactNode, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Table2, LineChart as LineIcon } from "lucide-react";
import { short } from "../format";

/* Chart primitives. Rules they follow:
   one y axis per chart, thin marks, hairline solid gridlines, 2px surface gaps between stacked
   segments, text in text tokens (never the series colour), a hover layer on every plot, and a
   table view of the same numbers behind a toggle. */

export interface Series { key: string; label: string; color: string }

function useWidth(): [React.RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / count;
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough;
  const whole = Math.max(step, max < count ? 1 : step);
  const ticks = [];
  for (let v = 0; v <= max + whole * 0.999; v += whole) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

function xTickIndexes(n: number, width: number, minGap = 64): number[] {
  if (n <= 1) return [0];
  const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(width / minGap))));
  const out = [];
  for (let i = n - 1; i >= 0; i -= every) out.unshift(i);
  return out;
}

export function ChartCard(props: {
  title: string; sub?: ReactNode; legend?: Series[]; children: ReactNode; fade?: boolean;
  table: { columns: string[]; rows: (string | number)[][] };
}) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="card">
      <div className="card-head">
        <div className="grow">
          <h2 className="card-title">{props.title}</h2>
          {props.sub && <div className="card-sub">{props.sub}</div>}
        </div>
        {props.legend && props.legend.length > 1 && !asTable && (
          <div className="legend" style={{ marginTop: 2 }}>
            {props.legend.map((s) => (
              <span className="legend-item" key={s.key}><span className="legend-swatch" style={{ background: s.color }} />{s.label}</span>
            ))}
          </div>
        )}
        <button className="btn ghost icon sm" style={{ width: 28 }} onClick={() => setAsTable(!asTable)}
          aria-label={asTable ? "Show chart" : "Show data table"} title={asTable ? "Show chart" : "Show data table"}>
          {asTable ? <LineIcon size={15} /> : <Table2 size={15} />}
        </button>
      </div>
      <div className={`card-body ${props.fade ? "loading-fade" : ""}`} style={asTable ? { padding: "8px 0 4px" } : undefined}>
        {asTable ? (
          <div className="table-wrap" style={{ maxHeight: 280, overflowY: "auto" }}>
            <table className="table">
              <thead><tr>{props.table.columns.map((c, i) => <th key={c} className={i ? "right" : ""}>{c}</th>)}</tr></thead>
              <tbody>
                {props.table.rows.map((row, i) => (
                  <tr key={i}>{row.map((cell, j) => <td key={j} className={j ? "right num" : ""}>{cell}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : props.children}
      </div>
    </section>
  );
}

interface TipState { index: number; x: number; y: number }

function Tooltip({ tip, title, rows }: { tip: TipState; title: string; rows: { label: string; value: string; color: string }[] }) {
  return (
    <div className="chart-tip" style={{ left: tip.x, top: tip.y - 10 }}>
      <div className="tip-title">{title}</div>
      {rows.map((r) => (
        <div className="tip-row" key={r.label}>
          <span className="tip-key" style={{ background: r.color }} />
          <span className="secondary">{r.label}</span>
          <span className="tip-val">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

const PAD = { top: 10, right: 12, bottom: 24, left: 40 };

/** Single-series trend line with a soft area wash and a crosshair readout. */
export function LineChart(props: {
  data: { label: string; value: number }[]; name: string; height?: number; format?: (n: number) => string;
}) {
  const [ref, width] = useWidth();
  const [tip, setTip] = useState<TipState | null>(null);
  const height = props.height ?? 220;
  const format = props.format ?? short;
  const { data } = props;
  const innerW = Math.max(10, width - PAD.left - PAD.right);
  const innerH = height - PAD.top - PAD.bottom;
  const ticks = useMemo(() => niceTicks(Math.max(1, ...data.map((d) => d.value))), [data]);
  const yMax = ticks[ticks.length - 1];
  const x = (i: number) => PAD.left + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
  const y = (v: number) => PAD.top + innerH - (v / yMax) * innerH;
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.value).toFixed(1)}`).join(" ");
  const area = data.length ? `${line} L${x(data.length - 1).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z` : "";

  const onMove = (e: React.PointerEvent) => {
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
    const ratio = (e.clientX - rect.left - PAD.left) / innerW;
    const index = Math.min(data.length - 1, Math.max(0, Math.round(ratio * (data.length - 1))));
    setTip({ index, x: x(index), y: y(data[index].value) });
  };

  return (
    <div className="chart" ref={ref} style={{ height }}>
      {width > 0 && (
        <svg height={height} role="img" aria-label={`${props.name} over time`} onPointerMove={onMove}
          onPointerLeave={() => setTip(null)}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end">{format(t)}</text>
            </g>
          ))}
          {xTickIndexes(data.length, innerW).map((i) => (
            <text key={i} x={x(i)} y={height - 6} textAnchor={i === data.length - 1 ? "end" : "middle"}>{data[i].label}</text>
          ))}
          {area && <path d={area} fill="var(--series-1)" opacity={0.1} />}
          <path d={line} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {tip && (
            <g>
              <line x1={tip.x} x2={tip.x} y1={PAD.top} y2={PAD.top + innerH} stroke="var(--axis)" />
              <circle cx={tip.x} cy={tip.y} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
            </g>
          )}
        </svg>
      )}
      {tip && <Tooltip tip={tip} title={data[tip.index].label}
        rows={[{ label: props.name, value: format(data[tip.index].value), color: "var(--series-1)" }]} />}
    </div>
  );
}

/** Stacked columns for a few series that share one unit and one axis. */
export function StackedColumns(props: {
  data: ({ label: string } & Record<string, number | string>)[]; series: Series[]; height?: number;
}) {
  const [ref, width] = useWidth();
  const [tip, setTip] = useState<TipState | null>(null);
  const height = props.height ?? 220;
  const { data, series } = props;
  const innerW = Math.max(10, width - PAD.left - PAD.right);
  const innerH = height - PAD.top - PAD.bottom;
  const totals = data.map((d) => series.reduce((sum, s) => sum + (Number(d[s.key]) || 0), 0));
  const ticks = useMemo(() => niceTicks(Math.max(1, ...totals)), [totals.join(",")]);
  const yMax = ticks[ticks.length - 1];
  const band = innerW / Math.max(1, data.length);
  const barW = Math.max(3, Math.min(24, band - 4));
  const y = (v: number) => PAD.top + innerH - (v / yMax) * innerH;
  const cx = (i: number) => PAD.left + band * i + band / 2;

  return (
    <div className="chart" ref={ref} style={{ height }}>
      {width > 0 && (
        <svg height={height} role="img" aria-label="Stacked column chart" onPointerLeave={() => setTip(null)}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end">{short(t)}</text>
            </g>
          ))}
          {xTickIndexes(data.length, innerW).map((i) => (
            <text key={i} x={cx(i)} y={height - 6} textAnchor="middle">{data[i].label}</text>
          ))}
          {data.map((d, i) => {
            let acc = 0;
            const present = series.filter((s) => Number(d[s.key]) > 0);
            return (
              <g key={i} opacity={tip && tip.index !== i ? 0.55 : 1}>
                {present.map((s, n) => {
                  const value = Number(d[s.key]);
                  const top = y(acc + value);
                  const bottom = y(acc);
                  acc += value;
                  const isTop = n === present.length - 1;
                  const h = Math.max(1, bottom - top - (n > 0 ? 2 : 0));
                  const r = isTop ? Math.min(4, barW / 2, h) : 0;
                  const x0 = cx(i) - barW / 2;
                  const path = `M${x0},${top + h} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + barW - r} Q${x0 + barW},${top} ${x0 + barW},${top + r} V${top + h} Z`;
                  return <path key={s.key} d={path} fill={s.color} />;
                })}
                <rect x={PAD.left + band * i} y={PAD.top} width={band} height={innerH} fill="transparent"
                  onPointerEnter={() => setTip({ index: i, x: cx(i), y: y(totals[i]) })} />
              </g>
            );
          })}
        </svg>
      )}
      {tip && <Tooltip tip={tip} title={String(data[tip.index].label)}
        rows={[...series].reverse().map((s) => ({ label: s.label, value: short(Number(data[tip.index][s.key]) || 0), color: s.color }))} />}
    </div>
  );
}

/** Ranked horizontal bars in one hue. Every value is printed at the bar tip, so no axis is needed. */
export function BarList(props: { items: { label: string; value: number; hint?: string }[]; format?: (n: number) => string; empty?: string }) {
  const max = Math.max(1, ...props.items.map((i) => i.value));
  const format = props.format ?? short;
  if (!props.items.length) return <div className="empty">{props.empty ?? "No data in this period"}</div>;
  return (
    <div className="barlist">
      {props.items.map((item) => (
        <div className="bar-row" key={item.label} title={item.hint ?? `${item.label}: ${format(item.value)}`}>
          <span className="bar-label">{item.label}</span>
          <span className="bar-track"><span className="bar" style={{ display: "block", width: `${(item.value / max) * 100}%` }} /></span>
          <span className="bar-value">{format(item.value)}</span>
        </div>
      ))}
    </div>
  );
}
