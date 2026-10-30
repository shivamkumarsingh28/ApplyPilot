"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { auth } from "@/lib/api";

const LINKS = [
  ["/", "Home"], ["/assistant", "Assistant"], ["/notices", "Notices"], ["/photo", "Photo studio"],
  ["/vault", "Vault"], ["/tracker", "Tracker"], ["/profile", "Profile"],
];

export default function Nav() {
  const path = usePathname();
  const router = useRouter();
  return (
    <header className="nav">
      <strong className="brand">ApplyPilot</strong>
      <nav>
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className={path === href || (href !== "/" && path.startsWith(href)) ? "active" : ""}>{label}</Link>
        ))}
      </nav>
      <button className="link" onClick={() => { auth.clear(); router.push("/login"); }}>Sign out</button>
    </header>
  );
}
