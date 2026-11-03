"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { auth } from "@/lib/api";
import { helpFor } from "@/lib/helpContent";
import ThemeToggle from "./ThemeToggle";

const MAIN = [
  ["/", "Home", "⌂"], ["/assistant", "Assistant", "✦"], ["/notices", "Notices", "▤"], ["/vault", "Vault", "▦"],
] as const;
const MORE = [
  ["/photo", "Photo studio"], ["/tracker", "Tracker"], ["/chat-apps", "Chat apps"], ["/extension", "Extension"],
  ["/profile", "Profile"], ["/settings", "Settings"],
] as const;
const ALL = [...MAIN.map(([h, l]) => [h, l] as const), ...MORE];

function active(path: string, href: string) {
  return path === href || (href !== "/" && path.startsWith(href));
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [more, setMore] = useState(false);
  const [help, setHelp] = useState(false);
  const h = helpFor(path);
  useEffect(() => { setMore(false); setHelp(false); }, [path]);

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Main">
        <strong className="brand">ApplyPilot</strong>
        <nav>
          {ALL.map(([href, label]) => (
            <Link key={href} href={href} className={active(path, href) ? "active" : ""} aria-current={active(path, href) ? "page" : undefined}>{label}</Link>
          ))}
        </nav>
        <div className="side-foot">
          <ThemeToggle />
          <button type="button" className="link" onClick={() => { auth.clear(); router.push("/login"); }}>Sign out</button>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topbar">
          <strong className="brand">ApplyPilot</strong>
          <span className="spacer" />
          <ThemeToggle />
          <button type="button" className="link" onClick={() => { auth.clear(); router.push("/login"); }}>Sign out</button>
        </header>
        <main className="container">{children}</main>
      </div>

      <button type="button" className="help-fab" onClick={() => setHelp(true)} aria-label="Help for this screen">? Help</button>
      {help && (
        <div className="drawer-backdrop" role="presentation" onClick={() => setHelp(false)}>
          <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Help: ${h.title}`} onClick={(e) => e.stopPropagation()}>
            <div className="card-head"><h2>Help: {h.title}</h2><button type="button" className="link" onClick={() => setHelp(false)} aria-label="Close help">✕</button></div>
            {h.body.map((p) => <p key={p}>{p}</p>)}
            {h.actions?.map((a) => <p key={a.href}><Link href={a.href} onClick={() => setHelp(false)}>{a.label} →</Link></p>)}
            <p className="muted small">Stuck? The assistant can also walk you through this screen.</p>
          </aside>
        </div>
      )}

      <nav className="bottombar" aria-label="Main">
        {MAIN.map(([href, label, icon]) => (
          <Link key={href} href={href} className={active(path, href) ? "active" : ""} aria-current={active(path, href) ? "page" : undefined}>
            <span aria-hidden="true">{icon}</span>{label}
          </Link>
        ))}
        <button type="button" className={MORE.some(([href]) => active(path, href)) ? "active" : ""} onClick={() => setMore(!more)} aria-expanded={more}>
          <span aria-hidden="true">•••</span>More
        </button>
      </nav>
      {more && (
        <div className="more-sheet" role="dialog" aria-label="More screens">
          {MORE.map(([href, label]) => <Link key={href} href={href} className={active(path, href) ? "active" : ""}>{label}</Link>)}
          <button type="button" className="link" onClick={() => setMore(false)}>Close</button>
        </div>
      )}
    </div>
  );
}
