import { isIndexablePersonStatus } from "@pdoom/contracts";
import { JsonLd } from "@/components/json-ld";
import { PersonProfile } from "@/components/person-profile";
import { loadDataset, loadPerson } from "@/lib/loaders";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, notFoundMetadata, pageMetadata, personFields } from "@/lib/seo";
import { personStructuredData } from "@/lib/structured-data";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [person, dataset] = await Promise.all([loadPerson(slug), loadDataset()]);
  if (!person) return notFoundMetadata();
  return pageMetadata(
    canonicalOrigin(),
    personFields({
      slug: person.slug,
      display_name: person.display_name,
      bio_short: person.bio_short,
      status: person.status,
      dataset_kind: dataset?.dataset_kind ?? null,
      indexable: isIndexablePersonStatus(person.status),
    }),
  );
}

export default async function PersonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [person, dataset] = await Promise.all([loadPerson(slug), loadDataset()]);
  if (!person) notFound();
  const indexable = isIndexablePersonStatus(person.status);
  const origin = canonicalOrigin();
  const nonce = await requestNonce();
  return (
    <>
      {indexable ? (
        <JsonLd
          nonce={nonce}
          data={personStructuredData({
            origin,
            slug: person.slug,
            display_name: person.display_name,
            bio_short: person.bio_short,
            dataset_kind: dataset?.dataset_kind ?? null,
            affiliations: person.affiliations,
            identities: person.identities,
          })}
        />
      ) : null}
      <PersonProfile person={person} />
    </>
  );
}
