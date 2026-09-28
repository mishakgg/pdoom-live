import { StatementAudit } from "@/components/statement-audit";
import { loadStatement } from "@/lib/loaders";
import { documentTitle } from "@/lib/presentation";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const statement = await loadStatement(slug);
  if (!statement) return { title: "Statement" };
  return { title: documentTitle(statement.person.display_name, statement.normalized_text) };
}

export default async function StatementPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const statement = await loadStatement(slug);
  if (!statement) notFound();
  return <StatementAudit statement={statement} />;
}
