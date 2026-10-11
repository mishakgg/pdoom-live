/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { loadDataset } from "@/lib/loaders";
import { DatasetNotice } from "./dataset-notice";

vi.mock("next/server", () => ({ connection: vi.fn(async () => undefined) }));
vi.mock("@/lib/loaders", () => ({ loadDataset: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("plainly identifies fictional people and evidence in the current synthetic dataset", async () => {
  vi.mocked(loadDataset).mockResolvedValue({ dataset_kind: "synthetic" } as NonNullable<Awaited<ReturnType<typeof loadDataset>>>);
  render(await DatasetNotice());
  const notice = screen.getByRole("note", { name: "Synthetic dataset notice" });
  expect(notice.textContent).toContain("Synthetic fixture dataset.");
  expect(notice.textContent).toContain("People, organizations, statements, and evidence are fictional.");
});

it.each(["live", null])("does not mislabel a %s dataset as synthetic", async (kind) => {
  vi.mocked(loadDataset).mockResolvedValue(kind ? { dataset_kind: kind } as NonNullable<Awaited<ReturnType<typeof loadDataset>>> : null);
  expect(await DatasetNotice()).toBeNull();
});

it("keeps the page available while explicitly disclosing a failed dataset-context read", async () => {
  vi.mocked(loadDataset).mockRejectedValue(new Error("private database details"));
  render(await DatasetNotice());
  expect(screen.getByRole("status").textContent).toContain("Dataset status is unavailable.");
  expect(document.body.textContent).not.toContain("private database details");
});
