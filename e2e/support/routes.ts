export type PublicRoute = {
  path: string;
  heading: string;
};

/** Major public routes exercised by accessibility and overflow checks. */
export const publicRoutes: PublicRoute[] = [
  { path: "/", heading: "Who said what, under which definition." },
  { path: "/people", heading: "Tracked people" },
  { path: "/people/ada-quill", heading: "Ada Quill" },
  { path: "/topics", heading: "Topics" },
  { path: "/topics/ai-extinction", heading: "Human extinction from AI" },
  { path: "/statements", heading: "Statements" },
  { path: "/statements/ada-extinction-2025", heading: "Ada Quill" },
  { path: "/statements/ada-misuse-2024", heading: "Ada Quill" },
  { path: "/statements/ada-inferred-2024", heading: "Ada Quill" },
  { path: "/statements/jonah-extinction-review-2024", heading: "Jonah Hale" },
  { path: "/sources", heading: "Sources" },
  { path: "/sources/ada-blog", heading: "Ada Quill notes" },
  { path: "/source-items/ada-essay-2023", heading: "A fictional note on extinction risk" },
  { path: "/source-items/riley-hostile-2025", heading: "Hostile fixture note" },
  { path: "/source-items/harbor-large-note", heading: "Large fixture body reference" },
  { path: "/trends", heading: "Trends" },
  { path: "/trends/extinction-by-2070-distribution", heading: "Unconditional human-extinction probability by 2070" },
  { path: "/methodology", heading: "Methodology" },
];

/** Routes measured by the performance smoke budget. */
export const performanceRoutes: PublicRoute[] = [
  { path: "/", heading: "Who said what, under which definition." },
  { path: "/people", heading: "Tracked people" },
  { path: "/people/ada-quill", heading: "Ada Quill" },
  { path: "/statements/ada-extinction-2025", heading: "Ada Quill" },
  { path: "/trends", heading: "Trends" },
  { path: "/methodology", heading: "Methodology" },
];
