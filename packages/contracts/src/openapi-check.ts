const FORBIDDEN_EXAMPLE_KEYS = [
  "extractor_version",
  "extraction_run",
  "extraction_run_slug",
  "prompt_contract_version",
  "model_name",
  "model_provider",
  "input_hash",
  "output_hash",
  "content_hash_input",
  "verification_detail",
  "attribution_detail",
  "collection_adapter",
  "rights_notes",
  "error_summary",
  "logical_key",
] as const;

export type OpenApiIssue = { path: string; message: string };

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function walkRefs(
  value: unknown,
  issues: OpenApiIssue[],
  components: { schemas: Set<string>; parameters: Set<string>; responses: Set<string> },
  path: string,
) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkRefs(item, issues, components, `${path}/${index}`));
    return;
  }
  if (!isObject(value)) return;
  if (typeof value.$ref === "string") {
    const match = /^#\/components\/(schemas|parameters|responses)\/([A-Za-z0-9_]+)$/.exec(value.$ref);
    const section = match?.[1] as "schemas" | "parameters" | "responses" | undefined;
    const name = match?.[2];
    if (!section || !name || !components[section].has(name)) {
      issues.push({ path, message: `unresolved $ref ${value.$ref}` });
    }
  }
  for (const [key, child] of Object.entries(value)) {
    if (key === "$ref") continue;
    walkRefs(child, issues, components, `${path}/${key}`);
  }
}

function walkExamples(value: unknown, issues: OpenApiIssue[], path: string) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkExamples(item, issues, `${path}/${index}`));
    return;
  }
  if (!isObject(value)) return;
  for (const key of FORBIDDEN_EXAMPLE_KEYS) {
    if (key in value) issues.push({ path, message: `example contains internal field ${key}` });
  }
  for (const [key, child] of Object.entries(value)) walkExamples(child, issues, `${path}/${key}`);
}

/**
 * Compact structural check for the public OpenAPI document.
 * Confirms the document is OpenAPI 3.0, every operation is a documented GET,
 * local schema refs resolve, and examples do not carry internal fields.
 */
export function validateOpenApiDocument(document: unknown, requiredPaths: readonly string[]): OpenApiIssue[] {
  const issues: OpenApiIssue[] = [];
  if (!isObject(document)) return [{ path: "/", message: "document must be an object" }];
  if (typeof document.openapi !== "string" || !document.openapi.startsWith("3.0.")) {
    issues.push({ path: "/openapi", message: "openapi version must be 3.0.x" });
  }
  if (!isObject(document.info) || typeof document.info.title !== "string" || typeof document.info.version !== "string") {
    issues.push({ path: "/info", message: "info.title and info.version are required" });
  }
  if (document.security !== undefined) {
    issues.push({ path: "/security", message: "the public API does not use an authentication scheme" });
  }
  const componentNames = {
    schemas: new Set<string>(),
    parameters: new Set<string>(),
    responses: new Set<string>(),
  };
  const components = document.components;
  if (!isObject(components) || !isObject(components.schemas)) {
    issues.push({ path: "/components/schemas", message: "components.schemas is required" });
  } else {
    for (const name of Object.keys(components.schemas)) componentNames.schemas.add(name);
    if (!componentNames.schemas.has("Error")) issues.push({ path: "/components/schemas/Error", message: "Error schema is required" });
    if (isObject(components.parameters)) {
      for (const name of Object.keys(components.parameters)) componentNames.parameters.add(name);
    }
    if (isObject(components.responses)) {
      for (const name of Object.keys(components.responses)) componentNames.responses.add(name);
    }
  }
  if (!isObject(document.paths)) {
    issues.push({ path: "/paths", message: "paths is required" });
    return issues;
  }
  const paths = document.paths;
  for (const required of requiredPaths) {
    if (!isObject(paths[required])) issues.push({ path: `/paths/${required}`, message: "required path is missing" });
  }
  for (const [path, item] of Object.entries(paths)) {
    if (path.includes("/health") || path.includes("/overview") || path.includes("ingestion")) {
      issues.push({ path: `/paths${path}`, message: "internal route is not part of the public API" });
    }
    if (!isObject(item) || !isObject(item.get)) {
      issues.push({ path: `/paths${path}`, message: "only GET operations are part of the public API" });
      continue;
    }
    const operation = item.get;
    if (typeof operation.operationId !== "string" || typeof operation.summary !== "string") {
      issues.push({ path: `/paths${path}/get`, message: "operationId and summary are required" });
    }
    if (!isObject(operation.responses) || !isObject(operation.responses["200"])) {
      issues.push({ path: `/paths${path}/get/responses`, message: "a 200 response is required" });
    }
    if (Array.isArray(operation.parameters)) {
      for (const [index, parameter] of operation.parameters.entries()) {
        if (isObject(parameter) && typeof parameter.$ref === "string") continue;
        if (!isObject(parameter) || typeof parameter.name !== "string" || typeof parameter.in !== "string" || !isObject(parameter.schema)) {
          issues.push({ path: `/paths${path}/get/parameters/${index}`, message: "parameter needs name, in, and schema" });
        }
      }
    }
    walkExamples(operation, issues, `/paths${path}/get`);
  }
  if (isObject(document.components)) walkExamples(document.components, issues, "/components");
  walkRefs(document, issues, componentNames, "");
  return issues;
}
