import Link from "next/link";
import { LiveSearch } from "./live-search";

const links: Array<[string, string]> = [
  ["/", "Activity"],
  ["/people", "People"],
  ["/topics", "Topics"],
  ["/statements", "Statements"],
  ["/sources", "Sources"],
  ["/trends", "Trends"],
  ["/methodology", "Method"],
];

export function SiteHeader({ pathname = "" }: { pathname?: string }) {
  return (
    <header className="mast">
      <Link className="brand" href="/">
        <em>pdoom</em>
        <span>.live</span>
      </Link>
      <nav className="nav" aria-label="Primary">
        {links.map(([href, label]) => (
          <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}>
            {label}
          </Link>
        ))}
      </nav>
      <LiveSearch />
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site">
      <p>
        pdoom.live records sourced statements. Explicit estimates, qualitative views, and model-inferred signals stay separate.
        This deployment is loaded with a synthetic fixture cohort.
      </p>
    </footer>
  );
}
