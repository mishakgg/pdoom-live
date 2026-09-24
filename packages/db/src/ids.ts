import { createHash } from "node:crypto";

const NAMESPACE = Buffer.from("a3c1e8e07b4a4e1a9c2d0b6f5e4d3c2a", "hex");

export function stableId(name: string): string {
  const hash = createHash("sha1");
  hash.update(NAMESPACE);
  hash.update(name, "utf8");
  const bytes = Buffer.from(hash.digest().subarray(0, 16));
  bytes[6] = ((bytes[6] ?? 0) & 0x0f) | 0x50;
  bytes[8] = ((bytes[8] ?? 0) & 0x3f) | 0x80;
  const hex = bytes.toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function sha256(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex");
}
