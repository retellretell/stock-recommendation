/**
 * 주식 관련 타입 정의
 */

export interface StockData {
  ticker: string;
  name: string;
  sector: string;
  probability: number;
  expected_return: number;
  fundamental_score: number;
  weather_icon: string;
  confidence: number;
}
export interface StockData {
  ticker: string;
  name: string;
  sector: string;
  probability: number;
  expected_return: number;
  fundamental_score: number;
  weather_icon: string;
  confidence: number;
  social_sentiment?: number;
  composite_score?: number;
  accessibility_label?: string;
  // 스마트 규칙 기반 예측 필드
  signal_direction?: 'BUY' | 'SELL' | 'HOLD';
  risk_level?: 'low' | 'medium' | 'high';
  top_reasons?: string[];
  technical_summary?: {
    rsi?: number;
    macd?: number;
    trend?: 'bullish' | 'bearish' | 'neutral';
  };
}

export interface RankingsData {
  top_gainers: StockData[];
  top_losers: StockData[];
  updated_at: string;
}

export interface PriceHistory {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FundamentalBreakdown {
  [key: string]: {
    raw_value: number;
    normalized: number;
    weight: number;
    contribution: number;
  };
}

export interface TechnicalIndicators {
  ma20: number;
  ma60: number;
  rsi: number;
  volatility: number;
}

export interface DetailedStock {
  ticker: string;
  name: string;
  sector: string;
  current_price: number;
  probability: number;
  expected_return: number;
  fundamental_breakdown: FundamentalBreakdown;
  price_history: PriceHistory[];
  news_sentiment?: number;
  technical_indicators: TechnicalIndicators;
  last_updated: string;
}

export interface SectorWeather {
  sector: string;
  probability: number;
  weather_icon: string;
  weather_desc: string;
  stock_count: number;
  top_stock: string;
}

export type Market = 'ALL' | 'KR' | 'US';
export type TabType = 'gainers' | 'losers';

export interface APIError {
  detail: string;
  type?: string;
}
