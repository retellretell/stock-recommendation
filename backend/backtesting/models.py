"""
백테스팅 데이터 모델
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class PredictionStatus(str, Enum):
    """예측 상태"""
    PENDING = "pending"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    EXPIRED = "expired"

class TradingAction(str, Enum):
    """거래 액션"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class Prediction(BaseModel):
    """예측 기록"""
    id: Optional[int] = None
    ticker: str
    prediction_date: datetime
    predicted_direction: str  # 'up', 'down'
    probability: float = Field(ge=0, le=1)
    expected_return: float
    confidence: float = Field(ge=0, le=1)
    
    # 실제 결과
    actual_price_1d: Optional[float] = None
    actual_price_3d: Optional[float] = None
    actual_price_7d: Optional[float] = None
    actual_return_1d: Optional[float] = None
    actual_return_3d: Optional[float] = None
    actual_return_7d: Optional[float] = None
    
    # 검증 정보
    status: PredictionStatus = PredictionStatus.PENDING
    checked_at: Optional[datetime] = None
    
    # 메타 정보
    model_version: str = "v1.0"
    features_used: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)

class PaperTrade(BaseModel):
    """가상 거래 기록"""
    id: Optional[int] = None
    prediction_id: int
    ticker: str
    action: TradingAction
    trade_date: datetime
    price: float
    quantity: int
    total_value: float
    
    # 포지션 정보
    position_before: int = 0
    position_after: int = 0
    cash_before: float
    cash_after: float
    
    # 수익률
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    commission: float = 0
    
    # 종료 정보
    closed_date: Optional[datetime] = None
    closed_price: Optional[float] = None
    final_pnl: Optional[float] = None

class Portfolio(BaseModel):
    """포트폴리오 상태"""
    cash: float
    positions: Dict[str, Dict[str, Any]]  # ticker -> {quantity, avg_price, current_price}
    total_value: float
    initial_capital: float
    
    # 성과 지표
    total_return: float
    total_return_pct: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    
    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    
    last_updated: datetime

class BacktestConfig(BaseModel):
    """백테스트 설정"""
    initial_capital: float = 10_000_000  # 1천만원
    commission_rate: float = 0.00015     # 0.015%
    tax_rate: float = 0.0023            # 0.23% (한국 증권거래세)
    max_position_size: float = 0.2       # 최대 20% per position
    stop_loss: float = 0.05             # 5% 손절
    take_profit: float = 0.10           # 10% 익절
    
    # 리밸런싱
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly
    min_trade_value: float = 100_000     # 최소 거래 금액
    
    # 백테스트 기간
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # 검증 설정
    check_intervals: List[int] = Field(default=[1, 3, 7])  # 일 단위
    confidence_threshold: float = 0.6     # 최소 신뢰도

class PerformanceMetrics(BaseModel):
    """성과 측정 지표"""
    period: str  # daily, weekly, monthly, all-time
    
    # 예측 정확도
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    
    # 방향별 정확도
    bullish_predictions: int
    bullish_correct: int
    bullish_accuracy: float
    bearish_predictions: int
    bearish_correct: int
    bearish_accuracy: float
    
    # 수익률별 정확도
    high_confidence_accuracy: float  # confidence > 0.7
    medium_confidence_accuracy: float  # 0.5 < confidence <= 0.7
    low_confidence_accuracy: float  # confidence <= 0.5
    
    # 거래 성과
    paper_trading_return: float
    paper_trading_return_pct: float
    benchmark_return: float  # KOSPI or S&P500
    alpha: float  # 초과 수익률
    
    # 리스크 지표
    volatility: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    
    # 섹터별 성과
    sector_performance: Dict[str, float]
    
    # 시간대별 성과
    best_hour: Optional[int] = None
    worst_hour: Optional[int] = None
    
    last_updated: datetime
