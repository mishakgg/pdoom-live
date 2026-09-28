import { curationEnabled } from "@pdoom/contracts";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Curation",
  robots: { index: false, follow: false },
};

export default function CurationLayout({ children }: { children: React.ReactNode }) {
  if (!curationEnabled()) notFound();
  return (
    <>
      <p className="kicker">Local curation · not a public page</p>
      {children}
    </>
  );
}
