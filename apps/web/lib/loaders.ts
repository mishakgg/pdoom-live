import { cache } from "react";
import { getPerson, getSource, getSourceItem, getStatement, getTopic, getTrend } from "@pdoom/db";

export const loadPerson = cache((slug: string) => getPerson(slug));
export const loadStatement = cache((slug: string) => getStatement(slug));
export const loadTopic = cache((slug: string) => getTopic(slug));
export const loadSource = cache((slug: string) => getSource(slug));
export const loadSourceItem = cache((slug: string) => getSourceItem(slug));
export const loadTrend = cache((slug: string) => getTrend(slug));
