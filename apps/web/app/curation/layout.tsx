import { curationEnabled } from "@pdoom/contracts";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default function CurationLayout({ children }: { children: React.ReactNode }) {
  if (!curationEnabled()) notFound();
  return (
    <>
      <p className="kicker">Local curation · not a public page</p>
      {children}
    </>
  );
}
