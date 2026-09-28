import { StatementAudit } from "@/components/statement-audit";
import { JsonLd } from "@/components/json-ld";
import { loadStatement, loadStatementDiscovery } from "@/lib/loaders";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, notFoundMetadata, pageMetadata, statementFields } from "@/lib/seo";
import { statementStructuredData } from "@/lib/structured-data";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const record = await loadStatementDiscovery(slug);
  if (!record) return notFoundMetadata();
  return pageMetadata(canonicalOrigin(), statementFields(record));
}

export default async function StatementPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [statement, discovery] = await Promise.all([loadStatement(slug), loadStatementDiscovery(slug)]);
  if (!statement || !discovery) notFound();
  const structured = statementStructuredData({ origin: canonicalOrigin(), ...discovery });
  const nonce = await requestNonce();
  return (
    <>
      {structured ? <JsonLd nonce={nonce} data={structured} /> : null}
      <StatementAudit statement={statement} />
    </>
  );
}
