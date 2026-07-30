export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  email: string;
}

export interface SettingsResponse {
  settings: Record<string, string>;
}

export interface Instrument {
  id: number;
  symbol: string;
  exchange: string;
  asset_class: string;
}

export interface InstrumentsResponse {
  instruments: Instrument[];
}

export interface Candle {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OhlcvResponse {
  instrument_id: number;
  timeframe: string;
  candles: Candle[];
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface IndicatorsResponse {
  instrument_id: number;
  timeframe: string;
  series: Record<string, IndicatorPoint[]>;
}

export interface PatternDetection {
  pattern: string;
  time: string;
  direction: string;
  confidence: number;
  explanation: string;
}

export interface PatternsResponse {
  instrument_id: number;
  timeframe: string;
  patterns: PatternDetection[];
}

export interface StrategySpec {
  type: string;
  fast: number;
  slow: number;
  period: number;
  low: number;
  high: number;
  signal: number;
  num_std: number;
}

/** For outgoing requests: only the parameters relevant to the chosen
 * strategy type need to be sent — the backend applies defaults for the
 * rest (docs/10, Strategy Builder). */
export type StrategySpecInput = { type: string } & Partial<
  Omit<StrategySpec, "type">
>;

export interface TradeDto {
  side: string;
  time?: string;
  executed_at?: string;
  price: number;
  quantity: number;
  fee: number;
  reason: string;
}

export interface EquityPoint {
  time: string;
  equity: number;
}

export interface BacktestReport {
  id: number | null;
  instrument_id: number;
  timeframe: string;
  strategy: StrategySpec;
  initial_capital: number;
  final_equity: number;
  total_return: number;
  max_drawdown: number;
  sharpe: number | null;
  win_rate: number | null;
  trade_count: number;
  trades: TradeDto[];
  equity_curve: EquityPoint[];
  explanation: string;
}

export interface BacktestSummary {
  id: number;
  instrument_id: number;
  timeframe: string;
  strategy: StrategySpec;
  initial_capital: number;
  final_equity: number;
  total_return: number;
  max_drawdown: number;
  trade_count: number;
  created_at: string;
}

export interface WalkForwardFold {
  fold: number;
  best_fast: number;
  best_slow: number;
  train_return: number;
  test_return: number;
}

export interface WalkForwardReport {
  instrument_id: number;
  timeframe: string;
  folds: WalkForwardFold[];
  mean_test_return: number;
  positive_test_folds: number;
  total_folds: number;
  explanation: string;
}

export interface PortfolioAnalytics {
  equity: number;
  cash: number;
  position_quantity: number;
  position_value: number;
  pnl: number;
  return_pct: number;
  fees_paid: number;
  trade_count: number;
}

export interface RiskReport {
  var_95: number | null;
  max_drawdown: number;
  annualized_volatility: number | null;
  explanation: string;
}

export interface PaperSession {
  id: number;
  instrument_id: number;
  timeframe: string;
  strategy: StrategySpec;
  initial_capital: number;
  status: string;
  started_at: string;
  stopped_at: string | null;
}

export interface PaperSessionDetail extends PaperSession {
  trades: TradeDto[];
  analytics: PortfolioAnalytics;
  risk: RiskReport;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface ModelScore {
  name: string;
  prob_up: number;
  test_accuracy: number;
}

export interface PredictionTrackRecord {
  bucket_low: number;
  bucket_high: number;
  bucket_resolved: number;
  bucket_accuracy: number | null;
  overall_resolved: number;
  overall_accuracy: number | null;
}

export interface PriceIntervalTrackRecord {
  resolved: number;
  empirical_coverage: number | null;
  declared_confidence: number;
}

export interface PriceTargetEstimate {
  current_price: number;
  expected_price: number;
  low_price: number;
  high_price: number;
  confidence: number;
  test_error_pct: number;
  track_record: PriceIntervalTrackRecord;
  explanation: string;
}

export interface DirectionPrediction {
  instrument_id: number;
  timeframe: string;
  as_of: string;
  horizon_candles: number;
  prob_up: number;
  prob_down: number;
  raw_prob_up: number;
  models: ModelScore[];
  test_accuracy: number;
  baseline_accuracy: number;
  training_rows: number;
  top_features: FeatureContribution[];
  track_record: PredictionTrackRecord;
  price_target: PriceTargetEstimate;
  explanation: string;
}

export interface SmcDetection {
  kind: string;
  time: string;
  direction: string;
  confidence: number;
  explanation: string;
}

export interface SmcResponse {
  instrument_id: number;
  timeframe: string;
  detections: SmcDetection[];
}

export interface EngineSignal {
  engine: string;
  direction: string;
  score: number;
  confidence: number;
  explanation: string;
}

export interface RegimeSummary {
  trend: string;
  volatility: string;
  is_trending: boolean;
  is_panic: boolean;
  label: string;
}

export interface MetaDecision {
  instrument_id: number;
  timeframe: string;
  direction: string;
  score: number;
  confidence: number;
  engines: EngineSignal[];
  regime: RegimeSummary | null;
  explanation: string;
}

export interface ConfidenceFactor {
  name: string;
  multiplier: number;
  explanation: string;
}

export interface GlobalConfidence {
  instrument_id: number;
  timeframe: string;
  direction: string;
  score: number;
  level: string;
  base_confidence: number;
  factors: ConfidenceFactor[];
  explanation: string;
}

export interface PairCorrelation {
  instrument_a: number;
  symbol_a: string;
  instrument_b: number;
  symbol_b: string;
  pearson: number | null;
  spearman: number | null;
  rolling: number | null;
  dynamic: number | null;
  sample_size: number;
  explanation: string;
}

export interface CorrelationMatrix {
  timeframe: string;
  window: number;
  instrument_ids: number[];
  pairs: PairCorrelation[];
  explanation: string;
}

export interface FeatureDrift {
  feature: string;
  psi: number | null;
  severity: string;
  explanation: string;
}

export interface LabelDrift {
  reference_up_rate: number | null;
  recent_up_rate: number | null;
  delta: number | null;
  severity: string;
  explanation: string;
}

export interface ConceptDrift {
  reference_accuracy: number | null;
  recent_accuracy: number | null;
  reference_n: number;
  recent_n: number;
  delta: number | null;
  severity: string;
  explanation: string;
}

export interface DriftReport {
  instrument_id: number;
  timeframe: string;
  overall_severity: string;
  feature_drifts: FeatureDrift[];
  label_drift: LabelDrift;
  concept_drift: ConceptDrift;
  explanation: string;
}

export interface FoldResult {
  fold: number;
  train_size: number;
  test_size: number;
  accuracy: number | null;
}

export interface CvSummary {
  method: string;
  folds: FoldResult[];
  mean_accuracy: number | null;
  std_accuracy: number | null;
  explanation: string;
}

export interface ModelValidation {
  instrument_id: number;
  timeframe: string;
  naive_split_accuracy: number | null;
  time_series_cv: CvSummary;
  purged_embargo_cv: CvSummary;
  nested_cv: CvSummary;
  explanation: string;
}

export interface BootstrapResult {
  mean: number;
  ci_low: number;
  ci_high: number;
  confidence: number;
  explanation: string;
}

export interface MonteCarloResult {
  observed_return: number;
  p_value: number;
  null_mean: number;
  null_std: number;
  explanation: string;
}

export interface WhiteRealityCheckResult {
  best_candidate_index: number;
  best_mean_return: number;
  p_value: number;
  n_candidates: number;
  explanation: string;
}

export interface BacktestValidation {
  instrument_id: number;
  timeframe: string;
  bootstrap: BootstrapResult;
  monte_carlo: MonteCarloResult;
  reality_check: WhiteRealityCheckResult;
  explanation: string;
}

export interface HpoTrial {
  trial: number;
  params: Record<string, number>;
  value: number | null;
}

export interface HpoResult {
  method: string;
  best_params: Record<string, number>;
  best_value: number | null;
  n_trials: number;
  trials: HpoTrial[];
  explanation: string;
}

export type HpoMethod = "grid" | "random" | "bayesian_optuna" | "bayesian_hyperopt";

export interface KellyResult {
  fraction: number;
  has_edge: boolean;
  explanation: string;
}

export interface PositionSizeResult {
  quantity: number;
  risk_amount: number;
  position_value: number;
  capital_at_risk_pct: number;
  explanation: string;
}

export interface StressScenario {
  shock_pct: number;
  resulting_value: number;
  loss_amount: number;
}

export interface RiskProfile {
  instrument_id: number;
  timeframe: string;
  var_95: number | null;
  expected_shortfall_95: number | null;
  max_drawdown: number;
  annualized_volatility: number | null;
  kelly: KellyResult;
  risk_of_ruin: number;
  position_sizing: PositionSizeResult;
  stress_test: StressScenario[];
  explanation: string;
}

export interface ExposureWarning {
  instrument: string;
  weight_pct: number;
  limit_pct: number;
  message: string;
}

export interface ExposureReport {
  warnings: ExposureWarning[];
  total_exposure_pct: number;
  max_single_pct: number;
  max_total_pct: number;
  explanation: string;
}

export interface RiskBudgetItem {
  instrument_id: number;
  symbol: string;
  current_weight_pct: number;
  target_weight_pct: number;
  annualized_volatility: number | null;
}

export interface RiskBudget {
  items: RiskBudgetItem[];
  explanation: string;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface ShapSnapshot {
  prediction_id: number;
  as_of: string;
  predicted_direction: string;
  contributions: FeatureContribution[];
}

export interface ShapHistory {
  instrument_id: number;
  timeframe: string;
  snapshots: ShapSnapshot[];
  explanation: string;
}

export interface GlobalImportanceItem {
  feature: string;
  mean_absolute_contribution: number;
  rank: number;
}

export interface GlobalImportance {
  instrument_id: number;
  timeframe: string;
  sample_size: number;
  items: GlobalImportanceItem[];
  explanation: string;
}

export interface FeatureTimePoint {
  as_of: string;
  contribution: number;
}

export interface FeatureEvolution {
  instrument_id: number;
  timeframe: string;
  feature: string;
  points: FeatureTimePoint[];
  explanation: string;
}

export interface ExplanationDelta {
  feature: string;
  contribution_a: number;
  contribution_b: number;
  delta: number;
}

export interface ExplanationComparison {
  prediction_id_a: number;
  prediction_id_b: number;
  similarity: number | null;
  deltas: ExplanationDelta[];
  explanation: string;
}

export interface ModelVersion {
  version: number;
  as_of: string;
  champion_model_type: string;
  xgboost_accuracy: number;
  logistic_regression_accuracy: number;
  ensemble_accuracy: number;
  baseline_accuracy: number;
  training_rows: number;
  is_champion: boolean;
  rolled_back: boolean;
}

export interface ModelRegistry {
  instrument_id: number;
  timeframe: string;
  versions: ModelVersion[];
  explanation: string;
}

export interface AbTestResult {
  instrument_id: number;
  timeframe: string;
  winner: string;
  xgboost_edge_mean: number;
  xgboost_edge_ci_low: number;
  xgboost_edge_ci_high: number;
  logistic_regression_edge_mean: number;
  logistic_regression_edge_ci_low: number;
  logistic_regression_edge_ci_high: number;
  sample_size: number;
  explanation: string;
}

export interface VolumeProfileBucket {
  price_low: number;
  price_high: number;
  volume: number;
}

export interface VolumeProfile {
  instrument_id: number;
  timeframe: string;
  buckets: VolumeProfileBucket[];
  point_of_control: VolumeProfileBucket | null;
  explanation: string;
}

export interface MarketRegime {
  instrument_id: number;
  timeframe: string;
  trend: string;
  volatility: string;
  is_trending: boolean;
  is_panic: boolean;
  confidence: number;
  label: string;
  explanation: string;
}

export interface NewsItem {
  source: string;
  title: string;
  link: string;
  published_at: string | null;
}

export interface HeadlineSentiment extends NewsItem {
  sentiment: string;
  score: number;
  rationale: string;
}

export interface SentimentResponse {
  items: HeadlineSentiment[];
  average_score: number;
  model: string;
  explanation: string;
}

export interface CalendarEvent {
  date: string;
  name: string;
  importance: string;
  note: string;
}

export interface CalendarResponse {
  events: CalendarEvent[];
  source_note: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  model: string;
  context_note: string;
  tools_invoked: string[];
  conversation_id: number;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
}

export interface ConversationSummary {
  id: number;
  title: string | null;
  updated_at: string;
}

export interface ConversationsResponse {
  conversations: ConversationSummary[];
}

export interface AssistantMemoryResponse {
  facts: string[];
}

export interface StrategyParameter {
  name: string;
  label: string;
  default: number;
  min: number;
  max: number;
}

export interface StrategyDefinition {
  type: string;
  label: string;
  description: string;
  parameters: StrategyParameter[];
}

export type AlertConditionType =
  | "price_above"
  | "price_below"
  | "rsi_above"
  | "rsi_below";

export interface Alert {
  id: number;
  instrument_id: number;
  timeframe: string;
  condition_type: AlertConditionType;
  threshold: number;
  is_active: boolean;
  message: string | null;
  created_at: string;
  triggered_at: string | null;
}

export interface MarketStatus {
  instrument_id: number;
  asset_class: string;
  is_open: boolean;
  next_open: string | null;
  next_close: string | null;
}

export interface PredictionRecord {
  id: number;
  instrument_id: number;
  symbol: string;
  timeframe: string;
  as_of: string;
  target_time: string;
  predicted_direction: "up" | "down";
  raw_prob_up: number;
  actual_direction: "up" | "down" | null;
  correct: boolean | null;
  resolved_at: string | null;
}

export interface CalibrationBucket {
  low: number;
  high: number;
  n: number;
  accuracy: number | null;
}

export interface AccuracyTrendPoint {
  index: number;
  resolved_at: string;
  rolling_accuracy: number;
  sample_size: number;
}

export interface TimeframeSummary {
  timeframe: string;
  resolved: number;
  pending: number;
  accuracy: number | null;
}

export interface PredictionDashboard {
  timeframe: string;
  summary: TimeframeSummary[];
  calibration: CalibrationBucket[];
  accuracy_trend: AccuracyTrendPoint[];
  recent: PredictionRecord[];
}

export interface TrainingSessionInfo {
  instrument_id: number;
  symbol: string;
  timeframe: string;
}

export interface TrainingSessionsResponse {
  sessions: TrainingSessionInfo[];
}

export interface InstrumentAllocation {
  instrument_id: number;
  symbol: string;
  asset_class: string;
  equity: number;
  weight_pct: number;
}

export interface PortfolioSummary {
  total_equity: number;
  total_initial_capital: number;
  total_pnl: number;
  total_return_pct: number;
  total_fees: number;
  running_sessions: number;
  stopped_sessions: number;
  allocation: InstrumentAllocation[];
  sessions: PaperSession[];
  explanation: string;
}

export interface ApiError {
  error: { code: string; message: string };
}
