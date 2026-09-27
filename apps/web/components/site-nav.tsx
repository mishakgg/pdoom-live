"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isNavCurrent } from "@/lib/presentation";

const links: Array<[string, string]> = [
  ["/", "Activity"],
  ["/people", "People"],
  ["/topics", "Topics"],
  ["/statements", "Statements"],
  ["/sources", "Sources"],
  ["/trends", "Trends"],
  ["/methodology", "Method"],
];

export function SiteNav() {
  const pathname = usePathname() || "/";
  return (
    <nav className="nav" aria-label="Primary">
      {links.map(([href, label]) => (
        <Link key={href} href={href} aria-current={isNavCurrent(pathname, href) ? "page" : undefined}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
