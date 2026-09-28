import { PARTIAL_COLLECTION_NOTE, unavailableCopy } from "@/lib/presentation";

export function EmptyState({
  kicker = "Coverage",
  title,
  children,
  heading = "h2",
}: {
  kicker?: string;
  title: string;
  children: React.ReactNode;
  heading?: "h2" | "h3";
}) {
  const Heading = heading;
  return (
    <section className="panel state">
      <p className="kicker">{kicker}</p>
      <Heading>{title}</Heading>
      <div className="state-body">{children}</div>
    </section>
  );
}

export function NoResults({ what }: { what: string }) {
  return (
    <EmptyState title={`No matching ${what}`} kicker="Filters">
      <p>Nothing in the current dataset matches these filters. Clearing a filter shows the wider collection. An empty filter result is not a finding about the subject.</p>
    </EmptyState>
  );
}

export function UnavailableState({
  collectionStatus,
  availability,
  heading = "h2",
}: {
  collectionStatus: string;
  availability: string;
  heading?: "h2" | "h3";
}) {
  const Heading = heading;
  return (
    <section className="panel state state-warning" role="status">
      <p className="kicker">Source material</p>
      <Heading>Source unavailable</Heading>
      <p>{unavailableCopy(collectionStatus, availability)}</p>
    </section>
  );
}

export function PartialCollectionNote() {
  return (
    <p className="state-inline" role="status">
      {PARTIAL_COLLECTION_NOTE}
    </p>
  );
}
