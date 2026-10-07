"use client";

import { useEffect, useRef, type ReactNode } from "react";

function omitEmptyFields(event: FormDataEvent) {
  // Change the submitted data, not the controls: canceled navigation and Back
  // must leave every filter editable. Preserve nonempty same-name entries.
  const names = new Set<string>();
  for (const [name, value] of event.formData) {
    if (typeof value === "string" && value.trim() === "") names.add(name);
  }
  for (const name of names) {
    const values = event.formData.getAll(name).filter((value) => typeof value !== "string" || value.trim() !== "");
    event.formData.delete(name);
    for (const value of values) event.formData.append(name, value);
  }
}

export function FilterForm({
  children,
  ...props
}: React.ComponentProps<"form"> & { children: ReactNode }) {
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const element = form.current;
    element?.addEventListener("formdata", omitEmptyFields);
    return () => element?.removeEventListener("formdata", omitEmptyFields);
  }, []);
  return <form {...props} ref={form}>{children}</form>;
}
