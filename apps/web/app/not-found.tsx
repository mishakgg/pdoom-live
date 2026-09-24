import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1>Not in the dataset</h1>
      <p>That record is not in the current database.</p>
      <Link href="/">Back to activity</Link>
    </>
  );
}
