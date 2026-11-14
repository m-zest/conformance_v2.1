import { createContext, FormEvent, useCallback, useContext, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Activity as ActivityIcon, Bell, Boxes, FlaskConical, KeyRound, LayoutDashboard, LogOut, Moon, ScrollText, Settings as SettingsIcon,
  ShieldCheck, SlidersHorizontal, Sparkles, Sun, Users,
} from "lucide-react";
import { api, useApi } from "./api";
import { Avatar, ErrorBox } from "./components/ui";
import Overview from "./pages/Overview";
import Alerts from "./pages/Alerts";
import ActivityPage from "./pages/Activity";
import { People, Person } from "./pages/People";
import Tools from "./pages/Tools";
import Copilot from "./pages/Copilot";
import Policies from "./pages/Policies";
import Audit from "./pages/Audit";
import SettingsPage from "./pages/Settings";

export interface Me { id: string; email: string; name: string; role: "admin" | "analyst" | "auditor"; default_password: boolean }
const MeContext = createContext<Me | null>(null);
export const useMe = () => useContext(MeContext)!;

function useTheme(): [string, () => void] {
  const read = () => {
    try { return localStorage.getItem("conformance-theme"); } catch { return null; }
  };
  const system = () => (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const [theme, setTheme] = useState<string>(() => read() ?? system());
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try { localStorage.setItem("conformance-theme", next); } catch { /* preference is not persisted */ }
  };
  return [theme, toggle];
}

function Login({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/login", { body: { email, password } });
      onSignedIn(await api<Me>("/auth/me"));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="login">
      <div className="card login-card">
        <div className="brand" style={{ padding: 0 }}>
          <span className="brand-mark"><ShieldCheck size={17} /></span>
          <div>
            <div className="brand-name">Conformance</div>
            <div className="brand-sub">AI usage governance</div>
          </div>
        </div>
        <form onSubmit={submit}>
          <label className="field"><span className="label">Email</span>
            <input className="input" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </label>
          <label className="field"><span className="label">Password</span>
            <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <ErrorBox message={error} />
          <button className="btn primary" disabled={busy}>{busy ? "Signing in" : "Sign in"}</button>
        </form>
      </div>
    </div>
  );
}

const NAV = [
  { label: "Monitor", items: [
    { to: "/", text: "Overview", icon: LayoutDashboard, end: true },
    { to: "/alerts", text: "Alerts", icon: Bell, count: true },
    { to: "/activity", text: "Activity", icon: ActivityIcon },
    { to: "/people", text: "People", icon: Users },
  ] },
  { label: "Coverage", items: [
    { to: "/tools", text: "Tools", icon: Boxes },
    { to: "/copilot", text: "Copilot", icon: Sparkles },
  ] },
  { label: "Govern", items: [
    { to: "/policies", text: "Policies", icon: SlidersHorizontal },
    { to: "/audit", text: "Audit", icon: ScrollText },
  ] },
  { label: "System", items: [{ to: "/settings", text: "Settings", icon: SettingsIcon }] },
];

function Shell({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
  const [theme, toggleTheme] = useTheme();
  const alerts = useApi<any>("/alerts?status=open&limit=1", 30000);
  const system = useApi<any>("/settings/system");
  const openCount = alerts.data?.counts?.open ?? 0;
  const demo = system.data?.demo;
  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Main">
        <div className="brand">
          <span className="brand-mark"><ShieldCheck size={17} /></span>
          <div>
            <div className="brand-name">Conformance</div>
            <div className="brand-sub">AI usage governance</div>
          </div>
        </div>
        {NAV.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-label">{group.label}</div>
            {group.items.map((item) => (
              <NavLink key={item.to} to={item.to} end={"end" in item} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
                <item.icon size={16} />
                {item.text}
                {"count" in item && openCount > 0 && <span className="nav-count">{openCount}</span>}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-foot">
          <div className="account">
            <Avatar name={me.name || me.email} />
            <div className="grow truncate">
              <div className="truncate" style={{ fontSize: 13, fontWeight: 550 }}>{me.name || me.email}</div>
              <div className="muted" style={{ fontSize: 11.5, textTransform: "capitalize" }}>{me.role}</div>
            </div>
            <button className="btn ghost icon sm" onClick={toggleTheme} aria-label="Switch colour theme" title="Switch colour theme">
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <button className="btn ghost icon sm" onClick={onSignOut} aria-label="Sign out" title="Sign out"><LogOut size={15} /></button>
          </div>
        </div>
      </nav>
      <div className="main">
        {me.default_password && (
          <div className="banner warn"><KeyRound size={15} />
            The administrator account still uses the default password. Change it under Settings before giving anyone else access.
          </div>
        )}
        {demo?.data && (
          <div className="banner"><FlaskConical size={15} />
            Demo data is loaded: synthetic activity for the fictional company {demo.data.company}. Requests you send through the gateway appear alongside it.
          </div>
        )}
        <main className="page">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/alerts/:id" element={<Alerts />} />
            <Route path="/activity" element={<ActivityPage />} />
            <Route path="/people" element={<People />} />
            <Route path="/people/:id" element={<Person />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/copilot" element={<Copilot />} />
            <Route path="/policies" element={<Policies />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const refresh = useCallback(() => {
    api<Me>("/auth/me").then(setMe).catch(() => setMe(null));
  }, []);
  useEffect(() => {
    refresh();
    const signedOut = () => setMe(null);
    window.addEventListener("conformance:signed-out", signedOut);
    return () => window.removeEventListener("conformance:signed-out", signedOut);
  }, [refresh]);
  if (me === undefined) return null;
  if (me === null) return <Login onSignedIn={setMe} />;
  const signOut = async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    setMe(null);
  };
  return <MeContext.Provider value={me}><Shell me={me} onSignOut={signOut} /></MeContext.Provider>;
}
