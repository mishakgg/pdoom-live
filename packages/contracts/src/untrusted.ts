/**
 * Source text is data. This wrapper exists so callers cannot confuse it
 * with an instruction, prompt, or executable fragment.
 */
export type UntrustedContent = {
  kind: "untrusted_content";
  text: string;
};

export function asUntrustedContent(text: string): UntrustedContent {
  return { kind: "untrusted_content", text };
}

export function untrustedText(value: UntrustedContent): string {
  return value.text;
}
