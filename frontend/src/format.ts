const int = new Intl.NumberFormat("en-US");
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

export const num = (n: number | null | undefined) => (n == null ? "0" : int.format(Math.round(n)));
export const short = (n: number | null | undefined) =>
  n == null ? "0" : Math.abs(n) < 10000 ? int.format(Math.round(n)) : compact.format(n);
export const pct = (n: number | null | undefined, digits = 1) => (n ?? 0).toFixed(digits) + "%";
export const money = (n: number | null | undefined) =>
  n == null ? "$0.00" : n >= 1000 ? "$" + compact.format(n) : "$" + n.toFixed(2);
export const ms = (n: number | null | undefined) =>
  n == null ? "" : n >= 1000 ? (n / 1000).toFixed(1) + " s" : (n < 10 ? n.toFixed(1) : Math.round(n)) + " ms";

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function fullDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return "never";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
  if (seconds < 86400) return Math.floor(seconds / 3600) + " h ago";
  const days = Math.floor(seconds / 86400);
  return days === 1 ? "yesterday" : days < 30 ? days + " days ago" : new Date(iso).toLocaleDateString();
}

export function bucketLabel(iso: string, unit: "hour" | "day"): string {
  const d = new Date(iso);
  return unit === "hour"
    ? d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}

export function initials(name: string | null | undefined): string {
  const parts = (name ?? "?").trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export const titleCase = (text: string) => text.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
