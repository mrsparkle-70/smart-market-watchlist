"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type IconName = "grid" | "list" | "sliders" | "pulse" | "bell";

const navItems: Array<{ href: string; label: string; detail: string; icon: IconName }> = [
  { href: "/dashboard", label: "Overview", detail: "Market brief", icon: "grid" },
  { href: "/watchlists", label: "Watchlists", detail: "Your symbols", icon: "list" },
  { href: "/settings", label: "Preferences", detail: "Scoring & alerts", icon: "sliders" },
];

function Icon({ name }: { name: IconName }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "grid") return <svg {...common}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>;
  if (name === "list") return <svg {...common}><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" strokeWidth="3" /></svg>;
  if (name === "sliders") return <svg {...common}><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="8" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="10" cy="18" r="2" /></svg>;
  if (name === "bell") return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>;
  return <svg {...common}><path d="M3 12h4l2.2-6 4.1 12 2.2-6H21" /></svg>;
}

function Brand() {
  return (
    <Link href="/dashboard" className="shell-brand" aria-label="Smart Market Watchlist home">
      <span className="shell-brand-mark">MW</span>
      <span className="shell-brand-copy">
        <strong>MarketWatch</strong>
        <small>intelligence desk</small>
      </span>
    </Link>
  );
}

function Sidebar({ pathname, onNavigate }: { pathname: string; onNavigate: () => void }) {
  return (
    <aside className="shell-sidebar">
      <div className="shell-sidebar-head"><Brand /></div>
      <div className="shell-section-label">Workspace</div>
      <nav className="shell-nav" aria-label="Primary navigation">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
          return (
            <Link key={item.href} href={item.href} onClick={onNavigate} className={`shell-nav-item ${active ? "is-active" : ""}`} aria-current={active ? "page" : undefined}>
              <span className="shell-nav-icon"><Icon name={item.icon} /></span>
              <span className="shell-nav-label"><strong>{item.label}</strong><small>{item.detail}</small></span>
              {active && <span className="shell-nav-pip" aria-hidden="true" />}
            </Link>
          );
        })}
      </nav>
      <div className="shell-sidebar-spacer" />
      <div className="shell-status-card">
        <div className="shell-status-heading"><span className="status-dot" /> Data connection</div>
        <p>Quotes are refreshed from your configured provider.</p>
        <span className="shell-status-live"><Icon name="pulse" /> FRESHNESS TRACKED</span>
      </div>
      <div className="shell-sidebar-footer">CODE 2026 · DELTA OVER DATA</div>
    </aside>
  );
}

function Topbar({ pathname, onMenu }: { pathname: string; onMenu: () => void }) {
  const current = navItems.find((item) => pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`)));
  return (
    <>
      <header className="shell-topbar">
        <button className="shell-menu-button" onClick={onMenu} aria-label="Open navigation"><span /><span /><span /></button>
        <div className="shell-breadcrumb"><span className="shell-breadcrumb-root">MARKET /</span><strong>{current?.label.toUpperCase() ?? "SYMBOL"}</strong></div>
        <div className="shell-topbar-actions">
          <span className="shell-market-clock"><span className="status-dot" /> US MARKET <b>●</b> MONITORING</span>
          <Link href="/settings" className="shell-icon-button" aria-label="Open preferences"><Icon name="bell" /></Link>
          <span className="shell-avatar" aria-hidden="true">S</span>
        </div>
      </header>
      <div className="shell-ticker" aria-label="Market data status">
        <span className="shell-ticker-label"><Icon name="pulse" /> SESSION PULSE</span>
        <span>Watchlist intelligence</span><i />
        <span>Changes ranked by signal strength</span><i />
        <span>Source freshness shown on every quote</span>
      </div>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const isPublic = pathname === "/login" || pathname === "/";

  useEffect(() => setMenuOpen(false), [pathname]);

  if (isPublic) return <>{children}</>;

  return (
    <div className={`app-shell ${menuOpen ? "nav-open" : ""}`}>
      <div className="shell-mobile-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      <Sidebar pathname={pathname} onNavigate={() => setMenuOpen(false)} />
      <div className="shell-main">
        <Topbar pathname={pathname} onMenu={() => setMenuOpen(true)} />
        <div className="shell-content">{children}</div>
      </div>
    </div>
  );
}
