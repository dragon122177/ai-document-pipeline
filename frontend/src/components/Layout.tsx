import {
  Activity,
  BookOpenCheck,
  Boxes,
  FileStack,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import { initials, label } from "../utils";

const allNavigation = [
  { to: "/", icon: LayoutDashboard, label: "Overview", roles: [] },
  { to: "/documents", icon: FileStack, label: "Documents", roles: [] },
  { to: "/review", icon: BookOpenCheck, label: "Review queue", roles: ["ADMIN", "REVIEWER"] },
  { to: "/search", icon: Search, label: "Knowledge search", roles: [] },
  { to: "/templates", icon: Boxes, label: "Templates", roles: [] },
  { to: "/audit", icon: ShieldCheck, label: "Audit trail", roles: ["ADMIN"] },
] as const;

const pageNames: Record<string, string> = {
  "/": "Operations overview",
  "/documents": "Document library",
  "/review": "Human review",
  "/search": "Knowledge search",
  "/templates": "Extraction templates",
  "/audit": "Audit trail",
};

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigation = allNavigation.filter(
    (item) => item.roles.length === 0 || item.roles.includes(user!.role as never),
  );

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <Sparkles size={20} />
          </span>
          <div>
            <strong>DocuFlux</strong>
            <span>Document intelligence</span>
          </div>
          <button
            className="icon-button mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={19} />
          </button>
        </div>

        <div className="workspace-label">Workspace</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map(({ to, icon: Icon, label: itemLabel }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <Icon size={18} />
              <span>{itemLabel}</span>
            </NavLink>
          ))}
        </nav>

        <div className="pipeline-health">
          <div className="pipeline-health-head">
            <Activity size={16} />
            <strong>Pipeline online</strong>
          </div>
          <p>Local intelligence · secure mode</p>
          <span><i /> Realtime events connected</span>
        </div>

        <div className="sidebar-user">
          <span className="avatar">{initials(user!.name)}</span>
          <div>
            <strong>{user!.name}</strong>
            <span>{label(user!.role)}</span>
          </div>
          <button className="icon-button" aria-label="Sign out" onClick={logout}>
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <section className="workspace">
        <div className="topbar">
          <button
            className="icon-button menu-button"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div>
            <span className="topbar-kicker">DocuFlux / Operations</span>
            <strong>{pageNames[location.pathname] ?? "Workspace"}</strong>
          </div>
          <div className="topbar-spacer" />
          <NavLink to="/search" className="global-search">
            <Search size={16} />
            <span>Search documents</span>
            <kbd>⌘ K</kbd>
          </NavLink>
          <span className="environment-pill">Demo environment</span>
        </div>
        <main className="main-content">
          <Outlet />
        </main>
      </section>
    </div>
  );
}
