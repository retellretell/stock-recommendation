"""
데이터 모델 정의 (Pydantic)
"""
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class Market(str, Enum):
    ALL = "ALL"
    KR = "KR"
    US = "US"

class StockData(BaseModel):
    ticker: str
    name: str
    sector: str
    current_price: float = Field(gt=0)
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    eps_yoy: Optional[float] = None
    revenue: Optional[float] = None
    revenue_yoy: Optional[float] = None
    roe: Optional[float] = None
    last_updated: datetime

class PriceHistory(BaseModel):
    date: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    
    @validator('high')
    def high_must_be_highest(cls, v, values):
        if 'low' in values and v < values['low']:
            raise ValueError('high must be >= low')
        return v

class FinancialMetrics(BaseModel):
    roe: Optional[float] = None
    eps_yoy: Optional[float] = None
    revenue_yoy: Optional[float] = None
    
    @validator('roe')
    def validate_roe(cls, v):
        if v is not None and not -100 <= v <= 100:
            raise ValueError(f"ROE {v}는 비정상적인 값입니다")
        return v
    
    @validator('eps_yoy', 'revenue_yoy')
    def validate_yoy(cls, v):
        if v is not None and not -200 <= v <= 500:
            raise ValueError(f"YoY {v}는 비정상적인 값입니다")
        return v
    
    def fill_missing_values(self, historical_data: Dict):
        """누락된 값을 과거 데이터로 채우기"""
        if self.roe is None:
            self.roe = historical_data.get('roe_prev_quarter', 0)
        if self.eps_yoy is None and 'eps' in historical_data and 'eps_prev_year' in historical_data:
            if historical_data['eps_prev_year'] != 0:
                self.eps_yoy = ((historical_data['eps'] - historical_data['eps_prev_year']) / 
                               abs(historical_data['eps_prev_year'])) * 100
        return self

class StockRanking(BaseModel):
    ticker: str
    name: str
    sector: str
    probability: float = Field(ge=0, le=1)
    expected_return: float
    fundamental_score: float = Field(ge=0, le=1)
    weather_icon: str
    confidence: float = Field(ge=0, le=1)

class DetailedStock(BaseModel):
    ticker: str
    name: str
    sector: str
    current_price: float = Field(gt=0)
    probability: float = Field(ge=0, le=1)
    expected_return: float
    fundamental_breakdown: Dict[str, Dict[str, float]]
    price_history: List[PriceHistory]
    news_sentiment: Optional[float] = Field(default=None, ge=-1, le=1)
    technical_indicators: Dict[str, float]
    last_updated: datetime

class RankingsResponse(BaseModel):
    top_gainers: List[StockRanking]
    top_losers: List[StockRanking]
    updated_at: datetime
    cache_info: Optional[Dict] = None

class SectorWeather(BaseModel):
    sector: str
    probability: float = Field(ge=0, le=1)
    weather_icon: str
    weather_desc: str
    stock_count: int = Field(ge=0)
    top_stock: str
