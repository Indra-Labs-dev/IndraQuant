import { useAuthStore } from "@/lib/stores/auth";

import type {
  BacktestReport,
  DirectionPrediction,
  SmcResponse,
  BacktestSummary,
  IndicatorsResponse,
  InstrumentsResponse,
  LoginResponse,
  OhlcvResponse,
  PaperSession,
  PaperSessionDetail,
  PatternsResponse,
  SettingsResponse,
  StrategySpecInput,
  UserProfile,
  WalkForwardReport,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8100/api/v1";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    let code = "unknown_error";
    let message = response.statusText;
    try {
      const body = await response.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      // Non-JSON error body: keep the HTTP status text.
    }
    if (response.status === 401) {
      useAuthStore.getState().setToken(null);
    }
    throw new ApiRequestError(response.status, code, message);
  }
  return response.json();
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<UserProfile> {
  return request("/auth/me");
}

export function getSettings(): Promise<SettingsResponse> {
  return request("/settings");
}

export function updateSetting(
  key: string,
  value: string,
): Promise<SettingsResponse> {
  return request(`/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export function getInstruments(): Promise<InstrumentsResponse> {
  return request("/instruments");
}

export function marketDataWsUrl(token: string): string {
  return `${BASE_URL.replace(/^http/, "ws")}/ws/market-data?token=${encodeURIComponent(token)}`;
}

export function getIndicators(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  indicators: string,
  limit = 500,
): Promise<IndicatorsResponse> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    indicators,
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/indicators?${params}`);
}

export function getPatterns(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  limit = 500,
): Promise<PatternsResponse> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/patterns?${params}`);
}

export interface BacktestParams {
  instrument_id: number;
  timeframe: string;
  from: Date;
  to: Date;
  strategy: StrategySpecInput;
  initial_capital: number;
}

export function runBacktest(params: BacktestParams): Promise<BacktestReport> {
  return request("/backtests", {
    method: "POST",
    body: JSON.stringify({
      ...params,
      from: params.from.toISOString(),
      to: params.to.toISOString(),
    }),
  });
}

export function listBacktests(): Promise<{ backtests: BacktestSummary[] }> {
  return request("/backtests");
}

export function runWalkForward(
  params: BacktestParams & { folds: number },
): Promise<WalkForwardReport> {
  return request("/backtests/walk-forward", {
    method: "POST",
    body: JSON.stringify({
      ...params,
      from: params.from.toISOString(),
      to: params.to.toISOString(),
    }),
  });
}

export function createPaperSession(params: {
  instrument_id: number;
  timeframe: string;
  strategy: StrategySpecInput;
  initial_capital: number;
}): Promise<PaperSession> {
  return request("/paper-trading/sessions", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function listPaperSessions(): Promise<{ sessions: PaperSession[] }> {
  return request("/paper-trading/sessions");
}

export function getPaperSession(id: number): Promise<PaperSessionDetail> {
  return request(`/paper-trading/sessions/${id}`);
}

export function stopPaperSession(id: number): Promise<PaperSession> {
  return request(`/paper-trading/sessions/${id}/stop`, { method: "POST" });
}

export function getPrediction(
  instrumentId: number,
  timeframe: string,
): Promise<DirectionPrediction> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/prediction?${params}`);
}

export function getMetaDecision(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").MetaDecision> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/meta-decision?${params}`);
}

export function getGlobalConfidenceScore(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").GlobalConfidence> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/confidence-score?${params}`);
}

export function getMarketRegime(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").MarketRegime> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/market-regime?${params}`);
}

export function getCorrelations(
  instrumentIds: number[],
  timeframe: string,
  window = 20,
): Promise<import("./types").CorrelationMatrix> {
  const params = new URLSearchParams({
    instrument_ids: instrumentIds.join(","),
    timeframe,
    window: String(window),
  });
  return request(`/correlations?${params}`);
}

export function getDriftReport(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").DriftReport> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/drift?${params}`);
}

export function getModelValidation(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").ModelValidation> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/model-validation?${params}`);
}

export function validateBacktest(
  params: BacktestParams,
): Promise<import("./types").BacktestValidation> {
  return request("/backtests/validation", {
    method: "POST",
    body: JSON.stringify({
      ...params,
      from: params.from.toISOString(),
      to: params.to.toISOString(),
    }),
  });
}

export function optimizeStrategy(params: {
  instrument_id: number;
  timeframe: string;
  from: Date;
  to: Date;
  strategy_type: string;
  method?: import("./types").HpoMethod;
  n_trials?: number;
  initial_capital?: number;
}): Promise<import("./types").HpoResult> {
  return request("/optimization/strategy", {
    method: "POST",
    body: JSON.stringify({
      ...params,
      from: params.from.toISOString(),
      to: params.to.toISOString(),
    }),
  });
}

export function optimizeModel(params: {
  instrument_id: number;
  timeframe: string;
  method?: import("./types").HpoMethod;
  n_trials?: number;
}): Promise<import("./types").HpoResult> {
  return request("/optimization/model", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getRiskProfile(
  instrumentId: number,
  timeframe: string,
  params?: { capital?: number; risk_per_trade_pct?: number; stop_distance_pct?: number },
): Promise<import("./types").RiskProfile> {
  const query = new URLSearchParams({ timeframe });
  if (params?.capital !== undefined) query.set("capital", String(params.capital));
  if (params?.risk_per_trade_pct !== undefined)
    query.set("risk_per_trade_pct", String(params.risk_per_trade_pct));
  if (params?.stop_distance_pct !== undefined)
    query.set("stop_distance_pct", String(params.stop_distance_pct));
  return request(`/instruments/${instrumentId}/risk-profile?${query}`);
}

export function getExposureReport(): Promise<import("./types").ExposureReport> {
  return request("/portfolio/exposure");
}

export function getRiskBudget(): Promise<import("./types").RiskBudget> {
  return request("/portfolio/risk-budget");
}

export function getShapHistory(
  instrumentId: number,
  timeframe: string,
  limit = 30,
): Promise<import("./types").ShapHistory> {
  const params = new URLSearchParams({ timeframe, limit: String(limit) });
  return request(`/instruments/${instrumentId}/shap-history?${params}`);
}

export function getGlobalFeatureImportance(
  instrumentId: number,
  timeframe: string,
  limit = 50,
): Promise<import("./types").GlobalImportance> {
  const params = new URLSearchParams({ timeframe, limit: String(limit) });
  return request(`/instruments/${instrumentId}/feature-importance?${params}`);
}

export function getFeatureEvolution(
  instrumentId: number,
  feature: string,
  timeframe: string,
  limit = 50,
): Promise<import("./types").FeatureEvolution> {
  const params = new URLSearchParams({ feature, timeframe, limit: String(limit) });
  return request(`/instruments/${instrumentId}/feature-evolution?${params}`);
}

export function compareExplanations(
  predictionIdA: number,
  predictionIdB: number,
): Promise<import("./types").ExplanationComparison> {
  return request(`/predictions/${predictionIdA}/compare/${predictionIdB}`);
}

export function getModelRegistry(
  instrumentId: number,
  timeframe: string,
  limit = 50,
): Promise<import("./types").ModelRegistry> {
  const params = new URLSearchParams({ timeframe, limit: String(limit) });
  return request(`/instruments/${instrumentId}/model-registry?${params}`);
}

export function runModelAbTest(
  instrumentId: number,
  timeframe: string,
): Promise<import("./types").AbTestResult> {
  const params = new URLSearchParams({ timeframe });
  return request(`/instruments/${instrumentId}/model-registry/ab-test?${params}`);
}

export function rollbackModelVersion(
  instrumentId: number,
  timeframe: string,
  version: number,
): Promise<{ instrument_id: number; timeframe: string; champion_version: number; explanation: string }> {
  const params = new URLSearchParams({ timeframe, version: String(version) });
  return request(`/instruments/${instrumentId}/model-registry/rollback?${params}`, {
    method: "POST",
  });
}

export function getVolumeProfile(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  bins = 10,
  limit = 500,
): Promise<import("./types").VolumeProfile> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    bins: String(bins),
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/volume-profile?${params}`);
}

export function getSmc(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  limit = 500,
): Promise<SmcResponse> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/smc?${params}`);
}

export function getNews(limit = 20): Promise<{ items: import("./types").NewsItem[] }> {
  return request(`/news?limit=${limit}`);
}

export function getNewsSentiment(
  limit = 8,
): Promise<import("./types").SentimentResponse> {
  return request(`/news/sentiment?limit=${limit}`);
}

export function getCalendarEvents(): Promise<import("./types").CalendarResponse> {
  return request("/calendar/events");
}

export function chatWithAssistant(
  message: string,
  history: import("./types").ChatMessage[],
): Promise<import("./types").ChatResponse> {
  return request("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}

export function listStrategies(): Promise<{
  strategies: import("./types").StrategyDefinition[];
}> {
  return request("/strategies");
}

export function createAlert(params: {
  instrument_id: number;
  timeframe: string;
  condition_type: import("./types").AlertConditionType;
  threshold: number;
}): Promise<import("./types").Alert> {
  return request("/alerts", { method: "POST", body: JSON.stringify(params) });
}

export function listAlerts(): Promise<{ alerts: import("./types").Alert[] }> {
  return request("/alerts");
}

export function deleteAlert(id: number): Promise<{ status: string }> {
  return request(`/alerts/${id}`, { method: "DELETE" });
}

export function getPredictionDashboard(
  timeframe: string,
  instrumentId?: number,
  limit = 100,
): Promise<import("./types").PredictionDashboard> {
  const params = new URLSearchParams({ timeframe, limit: String(limit) });
  if (instrumentId !== undefined) params.set("instrument_id", String(instrumentId));
  return request(`/predictions/dashboard?${params}`);
}

export function startTraining(
  timeframe: string,
  instrumentIds: number[],
): Promise<import("./types").TrainingSessionsResponse> {
  return request("/training/start", {
    method: "POST",
    body: JSON.stringify({ timeframe, instrument_ids: instrumentIds }),
  });
}

export function stopTraining(
  timeframe: string,
  instrumentIds: number[],
): Promise<import("./types").TrainingSessionsResponse> {
  return request("/training/stop", {
    method: "POST",
    body: JSON.stringify({ timeframe, instrument_ids: instrumentIds }),
  });
}

export function getTrainingSessions(): Promise<
  import("./types").TrainingSessionsResponse
> {
  return request("/training/sessions");
}

export function getPortfolioSummary(): Promise<
  import("./types").PortfolioSummary
> {
  return request("/portfolio/summary");
}

export function getMarketStatus(
  instrumentId: number,
): Promise<import("./types").MarketStatus> {
  return request(`/instruments/${instrumentId}/market-status`);
}

export function getOhlcv(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  limit = 500,
): Promise<OhlcvResponse> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/ohlcv?${params}`);
}
