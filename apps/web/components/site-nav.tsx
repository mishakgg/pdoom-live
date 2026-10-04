"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isNavCurrent } from "@/lib/presentation";

const research: Array<[string, string]> = [
  ["/", "Activity"],
  ["/people", "People"],
  ["/topics", "Topics"],
  ["/statements", "Statements"],
  ["/trends", "Trends"],
];

const reference: Array<[string, string]> = [
  ["/sources", "Sources"],
  ["/search", "Search"],
  ["/data", "Data"],
  ["/methodology", "Method"],
];

function NavLinks({ links }: { links: Array<[string, string]> }) {
  const pathname = usePathname() || "/";
  return (
    <>
      {links.map(([href, label]) => (
        <Link key={href} href={href} aria-current={isNavCurrent(pathname, href) ? "page" : undefined}>
          {label}
        </Link>
      ))}
    </>
  );
}

export function SiteNav() {
  return (
    <nav className="nav" aria-label="Primary">
      <NavLinks links={research} />
      <span className="nav-rule" aria-hidden="true" />
      <NavLinks links={reference} />
    </nav>
  );
}
