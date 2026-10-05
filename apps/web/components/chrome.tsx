import Link from "next/link";
import { LiveSearch } from "./live-search";
import { SiteNav } from "./site-nav";

export function SiteHeader() {
  return (
    <header className="mast">
      <div className="mast-bar">
        <Link className="brand" href="/">
          <em>pdoom</em>
          <span>.live</span>
        </Link>
        <SiteNav />
        <LiveSearch />
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site">
      <p>
        pdoom.live records sourced statements. Explicit estimates, qualitative views, and model-inferred signals stay separate.
        A synthetic fixture is marked synthetic. A live dataset describes its cohort and is not a census.
      </p>
      <p>
        <Link href="/methodology">Read the methodology</Link>
      </p>
    </footer>
  );
}
