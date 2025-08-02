"""
데이터 모델 정의 (Pydantic) - 개선된 버전
개인화, 접근성, 설명가능한 AI를 위한 새로운 모델 추가
"""
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class Market(str, Enum):
    ALL = "ALL"
    KR = "KR"
    US = "US"

class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class InvestmentStyle(str, Enum):
    GROWTH = "growth"
    VALUE = "value"
    DIVIDEND = "dividend"
    BALANCED = "balanced"

class ColorScheme(str, Enum):
    DEFAULT = "default"
    COLORBLIND = "colorblind"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"

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

# 새로운 모델들 추가

class ExplanationFactor(BaseModel):
    """예측 설명 요인"""
    name: str
    impact: float
    value: float
    description: str

class PredictionExplanation(BaseModel):
    """예측 설명"""
    top_positive_factors: List[ExplanationFactor]
    top_negative_factors: List[ExplanationFactor]
    feature_importance: List[Dict[str, float]]
    natural_language: str

class ExplainedPrediction(BaseModel):
    """설명 가능한 예측 결과"""
    probability: float = Field(ge=0, le=1)
    expected_return: float
    confidence: float = Field(ge=0, le=1)
    explanation: PredictionExplanation
    transparency_score: float = Field(ge=0, le=1)

class StockRanking(BaseModel):
    """개선된 주식 랭킹"""
    ticker: str
    name: str
    sector: str
    probability: float = Field(ge=0, le=1)
    expected_return: float
    fundamental_score: float = Field(ge=0, le=1)
    weather_icon: str
    confidence: float = Field(ge=0, le=1)
    social_sentiment: Optional[float] = Field(default=None, ge=0, le=1)
    composite_score: Optional[float] = Field(default=None, ge=0, le=1)
    accessibility_label: Optional[str] = None

class DetailedStock(BaseModel):
    """개선된 상세 종목 정보"""
    ticker: str
    name: str
    sector: str
    current_price: float = Field(gt=0)
    probability: float = Field(ge=0, le=1)
    expected_return: float
    fundamental_breakdown: Dict[str, Dict[str, float]]
    price_history: List[PriceHistory]
    news_sentiment: Optional[float] = Field(default=None, ge=-1, le=1)
    social_sentiment: Optional[float] = Field(default=None, ge=0, le=1)
    technical_indicators: Dict[str, float]
    last_updated: datetime

class RankingsResponse(BaseModel):
    """개선된 랭킹 응답"""
    top_gainers: List[StockRanking]
    top_losers: List[StockRanking]
    updated_at: datetime
    cache_info: Optional[Dict] = None
    user_personalized: bool = False

class SectorWeather(BaseModel):
    """개선된 섹터 날씨"""
    sector: str
    probability: float = Field(ge=0, le=1)
    weather_icon: str
    weather_desc: str
    stock_count: int = Field(ge=0)
    top_stock: str
    trend_strength: Optional[float] = Field(default=None, ge=0, le=1)

# 사용자 개인화 모델

class UIPreferences(BaseModel):
    """UI 선호 설정"""
    info_density: str = 'medium'  # low, medium, high
    chart_type: str = 'candlestick'  # line, candlestick, area
    color_scheme: ColorScheme = ColorScheme.DEFAULT
    language: str = 'ko'  # ko, en
    reduce_motion: bool = False
    show_tooltips: bool = True
    font_size: str = 'normal'  # small, normal, large

class UserPreferences(BaseModel):
    """사용자 선호도"""
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    preferred_sectors: List[str] = Field(default_factory=list)
    investment_style: InvestmentStyle = InvestmentStyle.BALANCED
    ui_preferences: Optional[UIPreferences] = None

class PersonalizedDashboard(BaseModel):
    """개인화된 대시보드 설정"""
    user_id: str
    layout: str
    widgets: List[str]
    risk_filters: Dict[str, Any]
    preferred_sectors: List[str]
    theme: str
    language: str

# 백테스팅 모델

class BacktestPeriod(BaseModel):
    """백테스트 기간"""
    start: str
    end: str
    trading_days: int

class MarketConditionAnalysis(BaseModel):
    """시장 상황별 분석"""
    total_trades: int
    win_rate: float = Field(ge=0, le=1)
    avg_return: float
    total_return: float

class RiskMetrics(BaseModel):
    """리스크 메트릭"""
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    volatility: float
    downside_volatility: float

class DrawdownAnalysis(BaseModel):
    """드로다운 분석"""
    max_drawdown: float
    avg_drawdown: float
    total_drawdowns: int
    avg_duration_days: float
    avg_recovery_days: float
    current_drawdown: float
    drawdown_periods: List[Dict]

class BacktestResults(BaseModel):
    """백테스트 결과"""
    period: BacktestPeriod
    overall_performance: Dict[str, float]
    accuracy_metrics: Dict[str, float]
    risk_metrics: RiskMetrics
    market_condition_analysis: Dict[str, MarketConditionAnalysis]
    drawdown_analysis: DrawdownAnalysis
    trade_statistics: Dict[str, Any]
    monthly_returns: List[Dict[str, Any]]

# 학습 콘텐츠 모델

class LearningContent(BaseModel):
    """학습 콘텐츠"""
    id: str
    title: str
    topics: List[str]
    duration: str
    difficulty: str
    experience_level: ExperienceLevel

class LearningTip(BaseModel):
    """학습 팁"""
    title: str
    content: str
    icon: str

# API 응답 모델

class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    checks: Dict[str, bool]
    metrics: Optional[Dict[str, Any]] = None
    timestamp: str
    environment: str

class MarketOverview(BaseModel):
    """시장 개요"""
    status: str  # overheated, bullish, neutral, bearish, oversold
    temperature: int = Field(ge=0, le=100)
    description: str
    strongest_sectors: List[str]
    weakest_sectors: List[str]

class SectorWeatherResponse(BaseModel):
    """섹터 날씨 응답"""
    sectors: List[SectorWeather]
    market_overview: MarketOverview
    updated_at: str

# 접근성 모델

class AccessibilitySettings(BaseModel):
    """접근성 설정"""
    high_contrast: bool = False
    font_size: str = 'normal'
    reduce_motion: bool = False
    screen_reader_mode: bool = False
    keyboard_navigation: bool = True
    color_blind_mode: Optional[str] = None  # protanopia, deuteranopia, tritanopia

# 에러 응답 모델

class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    path: Optional[str] = None
    suggestion: Optional[str] = None

# 검증 함수들

def validate_date_range(start_date: str, end_date: str) -> bool:
    """날짜 범위 검증"""
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        return start < end and (end - start).days <= 365 * 5  # 최대 5년
    except:
        return False

def validate_ticker_format(ticker: str) -> bool:
    """티커 형식 검증"""
    # 한국: 6자리 숫자 + .KS/.KQ
    # 미국: 1-5자리 알파벳
    import re
    kr_pattern = r'^\d{6}\.(KS|KQ)
    us_pattern = r'^[A-Z]{1,5}
    
    return bool(re.match(kr_pattern, ticker) or re.match(us_pattern, ticker))
