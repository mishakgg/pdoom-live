export {
  computeHistoricalRevision,
  computeProbabilityDistribution,
  computeProbabilityDistribution as computeExplicitNumericDistribution,
  computeQuantityForecast,
  computeStatementVolume,
  computeTimelineForecast,
  discoverQuestionTrends,
  median,
} from "./trend-engine";

export type {
  DiscoveredTrend,
  Exclusion,
  IncludedEstimate,
  NumericTrendResult,
  RepeatRecord,
  RevisionChain,
  RevisionEdge,
  RevisionLink,
  RevisionPoint,
  RevisionResult,
  TrendCandidate,
  TrendCoverage,
  TrendScope,
  VolumeRow,
} from "./trend-engine";
