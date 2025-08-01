"""
애플리케이션 설정 관리
"""
from pydantic import BaseSettings, validator
from typing import List, Dict
import os

class Settings(BaseSettings):
    """애플리케이션 설정"""
    # API Keys
    krx_api_key: str = ""
    dart_api_key: str = ""
    
    # Environment
    env: str = "development"
    
    # Cache Settings
    cache_ttl: int = 10800  # 3 hours
    cache_freshness: int = 3600  # 1 hour
    cache_db_path: str = "cache.db"
    
    # API Settings
    batch_size: int = 100
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    max_concurrent_requests: int = 5
    
    # Model Settings
    model_update_interval: int = 604800  # 1 week
    prediction_confidence_threshold: float = 0.6
    
    # CORS Settings
    @property
    def allowed_origins(self) -> List[str]:
        if self.env == "production":
            return ["https://stock-weather.vercel.app"]
        return ["http://localhost:3000", "http://localhost:3001"]
    
    # Behavior Thresholds
    behavior_thresholds: Dict[str, float] = {
        'high_turnover': 2.0,
        'short_holding': 7,
        'high_volatility': 0.15,
        'sector_concentration': 0.3,
        'loss_delay': 0.3,
        'fomo_threshold': 0.05,
        'min_cash_ratio': 0.1
    }
    
    # Target KPIs
    target_kpi: Dict[str, float] = {
        'avg_holding_period': 7,
        'monthly_turnover': 30,
        'win_rate': 60,
        'portfolio_volatility': 12,
        'fomo_count': 5
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("krx_api_key", "dart_api_key")
    def validate_api_keys(cls, v, field):
        if not v and os.getenv("ENV") == "production":
            raise ValueError(f"{field.name} is required in production")
        return v
    
    def validate_settings(self):
        """시작 시 필수 설정 검증"""
        if self.env == "production":
            if not self.krx_api_key:
                raise ValueError("KRX API 키가 필요합니다")
            if not self.dart_api_key:
                raise ValueError("DART API 키가 필요합니다")
        return True

# 싱글톤 인스턴스
settings = Settings()
