import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Not in the dataset",
  description: "That record is not in the current public dataset.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <>
      <h1>Not in the dataset</h1>
      <p>That record is not in the current database.</p>
      <Link href="/">Back to activity</Link>
    </>
  );
}
