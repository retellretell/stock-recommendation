"""
백테스팅 설정
"""
from typing import Dict, List
from pydantic import BaseSettings

class BacktestingSettings(BaseSettings):
    """백테스팅 전용 설정"""
    
    # 데이터베이스
    backtesting_db_path: str = "backtesting.db"
    
    # 거래 설정
    initial_capital: float = 10_000_000  # 1천만원
    commission_rate: float = 0.00015     # 0.015%
    tax_rate: float = 0.0023            # 0.23%
    slippage: float = 0.001             # 0.1% 슬리피지
    
    # 포지션 관리
    max_positions: int = 10              # 최대 보유 종목 수
    max_position_size: float = 0.2       # 종목당 최대 20%
    min_position_size: float = 0.02      # 종목당 최소 2%
    min_trade_value: float = 100_000     # 최소 거래 금액
    
    # 리스크 관리
    stop_loss: float = 0.05             # 5% 손절
    take_profit: float = 0.10           # 10% 익절
    trailing_stop: float = 0.03         # 3% 트레일링 스톱
    max_drawdown_limit: float = 0.25    # 25% 최대 낙폭
    
    # 신호 설정
    confidence_threshold: float = 0.6    # 최소 신뢰도
    probability_buy_threshold: float = 0.65   # 매수 확률 임계값
    probability_sell_threshold: float = 0.35  # 매도 확률 임계값
    
    # 리밸런싱
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly
    rebalance_threshold: float = 0.05    # 5% 이상 벗어나면 리밸런싱
    
    # 검증 설정
    check_intervals: List[int] = [1, 3, 7]    # 예측 확인 간격 (일)
    backtest_period_days: int = 180           # 백테스트 기간
    walk_forward_days: int = 30               # 워크포워드 기간
    
    # 성과 측정
    benchmark_ticker: str = "^KS11"      # KOSPI 지수
    risk_free_rate: float = 0.03         # 연 3% 무위험 수익률
    
    # 섹터 설정
    sector_weights: Dict[str, float] = {
        "IT": 0.2,
        "전자": 0.2,
        "바이오": 0.15,
        "금융": 0.15,
        "화학": 0.1,
        "자동차": 0.1,
        "기타": 0.1
    }
    
    # 스케줄링
    morning_routine_time: str = "09:00"
    afternoon_check_time: str = "16:00"
    daily_report_time: str = "22:00"
    
    # 알림 설정
    enable_notifications: bool = True
    notification_channels: List[str] = ["log", "email"]
    alert_thresholds: Dict[str, float] = {
        "accuracy_low": 0.45,
        "accuracy_high": 0.65,
        "drawdown_warning": 0.15,
        "drawdown_critical": 0.25,
        "daily_loss": 0.03,
        "daily_gain": 0.05
    }
    
    # 데이터 관리
    data_retention_days: int = 90        # 데이터 보관 기간
    cleanup_old_predictions: bool = True
    
    # 디버그
    debug_mode: bool = False
    log_trades: bool = True
    save_predictions: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "BACKTEST_"

# 싱글톤 인스턴스
backtest_settings = BacktestingSettings()
