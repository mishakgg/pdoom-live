"use client";

import type { FormEvent, ReactNode } from "react";

function omitEmptyFields(event: FormEvent<HTMLFormElement>) {
  for (const element of Array.from(event.currentTarget.elements)) {
    if (!(element instanceof HTMLInputElement || element instanceof HTMLSelectElement)) continue;
    if (!element.name || element.disabled || element.type === "submit" || element.type === "button") continue;
    if (element.value.trim() === "") element.disabled = true;
  }
}

export function FilterForm({
  children,
  onSubmit,
  ...props
}: React.ComponentProps<"form"> & { children: ReactNode }) {
  return (
    <form
      {...props}
      onSubmit={(event) => {
        omitEmptyFields(event);
        onSubmit?.(event);
      }}
    >
      {children}
    </form>
  );
}
