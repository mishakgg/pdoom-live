import { PersonProfile } from "@/components/person-profile";
import { loadPerson } from "@/lib/loaders";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const person = await loadPerson(slug);
  return { title: person?.display_name ?? "Person" };
}

export default async function PersonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const person = await loadPerson(slug);
  if (!person) notFound();
  return <PersonProfile person={person} />;
}
