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

export interface ApiError {
  error: { code: string; message: string };
}
