import {
  getDatasetRecord,
  getPerson,
  getSource,
  getSourceItem,
  getSourceItemDiscovery,
  getStatement,
  getStatementDiscovery,
  getTopic,
  getTrend,
} from "@pdoom/db";
import { cache } from "react";

export const loadDataset = cache(() => getDatasetRecord());
export const loadPerson = cache((slug: string) => getPerson(slug));
export const loadStatement = cache((slug: string) => getStatement(slug));
export const loadStatementDiscovery = cache((slug: string) => getStatementDiscovery(slug));
export const loadTopic = cache((slug: string) => getTopic(slug));
export const loadSource = cache((slug: string) => getSource(slug));
export const loadSourceItem = cache((slug: string) => getSourceItem(slug));
export const loadSourceItemDiscovery = cache((slug: string) => getSourceItemDiscovery(slug));
export const loadTrend = cache((slug: string) => getTrend(slug));
