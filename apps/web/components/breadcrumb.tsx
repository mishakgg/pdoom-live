import Link from "next/link";

export function Breadcrumb({ items }: { items: Array<{ href?: string; label: string }> }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      <ol>
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`}>
              {item.href && !last ? <Link href={item.href}>{item.label}</Link> : <span aria-current="page">{item.label}</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
