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
