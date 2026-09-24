import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { canonicalImportSchema } from "./schemas";

const schema = z.toJSONSchema(canonicalImportSchema, {
  target: "draft-7",
  unrepresentable: "any",
});

const out = resolve(dirname(fileURLToPath(import.meta.url)), "../schema/canonical-import.schema.json");
writeFileSync(out, `${JSON.stringify(schema, null, 2)}\n`);
console.log(`wrote ${out}`);
