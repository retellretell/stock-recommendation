"""
예측 추적 및 검증 시스템
"""
import aiosqlite
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import asyncio

from .models import Prediction, PredictionStatus, PerformanceMetrics
from ..alpha_vantage_client import AlphaVantageClient

logger = structlog.get_logger()

class PredictionTracker:
    """예측 결과 자동 추적"""
    
    def __init__(self, db_path: str = "backtesting.db"):
        self.db_path = db_path
        self.alpha_vantage = AlphaVantageClient()
        self._initialized = False
        
    async def initialize(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            # 예측 테이블
            await db.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    prediction_date TIMESTAMP NOT NULL,
                    predicted_direction TEXT NOT NULL,
                    probability REAL NOT NULL,
                    expected_return REAL NOT NULL,
                    confidence REAL NOT NULL,
                    
                    actual_price_1d REAL,
                    actual_price_3d REAL,
                    actual_price_7d REAL,
                    actual_return_1d REAL,
                    actual_return_3d REAL,
                    actual_return_7d REAL,
                    
                    status TEXT NOT NULL DEFAULT 'pending',
                    checked_at TIMESTAMP,
                    
                    model_version TEXT,
                    features_used TEXT,
                    reasons TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 성과 메트릭 테이블
            await db.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_prediction_date 
                ON predictions(prediction_date)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker 
                ON predictions(ticker)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON predictions(status)
            """)
            
            await db.commit()
            
        self._initialized = True
        logger.info("prediction_tracker_initialized", db_path=self.db_path)
    
    async def save_prediction(self, 
                            ticker: str, 
                            prediction: Dict,
                            current_price: float) -> int:
        """예측 저장"""
        if not self._initialized:
            await self.initialize()
            
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO predictions (
                    ticker, prediction_date, predicted_direction,
                    probability, expected_return, confidence,
                    model_version, features_used, reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                datetime.now().isoformat(),
                'up' if prediction['probability'] > 0.5 else 'down',
                prediction['probability'],
                prediction['expected_return'],
                prediction.get('confidence', 0.5),
                prediction.get('model_version', 'v1.0'),
                json.dumps(prediction.get('features', {})),
                json.dumps(prediction.get('top_reasons', []))
            ))
            
            await db.commit()
            prediction_id = cursor.lastrowid
            
        logger.info("prediction_saved", 
                   ticker=ticker, 
                   prediction_id=prediction_id,
                   probability=prediction['probability'])
        
        return prediction_id
    
    async def check_predictions(self, days_after: int = 1):
        """예측 결과 확인"""
        if not self._initialized:
            await self.initialize()
            
        check_date = datetime.now() - timedelta(days=days_after)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 확인할 예측들 조회
            cursor = await db.execute("""
                SELECT * FROM predictions 
                WHERE status = 'pending' 
                AND prediction_date <= ?
                AND actual_price_{}_d IS NULL
            """.format(days_after), (check_date.isoformat(),))
            
            predictions = await cursor.fetchall()
            
        checked_count = 0
        for pred in predictions:
            try:
                # 실제 가격 조회
                actual_price = await self._get_actual_price(
                    pred['ticker'], 
                    pred['prediction_date'],
                    days_after
                )
                
                if actual_price:
                    await self._update_prediction_result(
                        pred['id'], 
                        pred['ticker'],
                        pred['prediction_date'],
                        days_after, 
                        actual_price
                    )
                    checked_count += 1
                    
            except Exception as e:
                logger.error("check_prediction_error", 
                           prediction_id=pred['id'], 
                           error=str(e))
        
        logger.info("predictions_checked", 
                   days_after=days_after, 
                   checked_count=checked_count)
        
        return checked_count
    
    async def _get_actual_price(self, 
                              ticker: str, 
                              prediction_date: str,
                              days_after: int) -> Optional[float]:
        """실제 가격 조회"""
        target_date = datetime.fromisoformat(prediction_date) + timedelta(days=days_after)
        
        # 주말 처리 (다음 영업일로)
        while target_date.weekday() >= 5:  # 토요일(5), 일요일(6)
            target_date += timedelta(days=1)
        
        # Alpha Vantage에서 가격 조회
        try:
            stock_data = await self.alpha_vantage.get_daily_prices(ticker)
            
            # 해당 날짜의 종가 찾기
            date_str = target_date.strftime('%Y-%m-%d')
            if date_str in stock_data:
                return stock_data[date_str]['close']
            
            # 정확한 날짜가 없으면 가장 가까운 날짜
            dates = sorted(stock_data.keys(), reverse=True)
            for date in dates:
                if date <= date_str:
                    return stock_data[date]['close']
                    
        except Exception as e:
            logger.error("get_actual_price_error", ticker=ticker, error=str(e))
            
        return None
    
    async def _update_prediction_result(self,
                                      prediction_id: int,
                                      ticker: str,
                                      prediction_date: str,
                                      days_after: int,
                                      actual_price: float):
        """예측 결과 업데이트"""
        # 예측 당시 가격 조회
        base_price = await self._get_actual_price(ticker, prediction_date, 0)
        if not base_price:
            return
            
        # 실제 수익률 계산
        actual_return = (actual_price - base_price) / base_price * 100
        
        async with aiosqlite.connect(self.db_path) as db:
            # 결과 업데이트
            await db.execute("""
                UPDATE predictions 
                SET actual_price_{0}_d = ?,
                    actual_return_{0}_d = ?,
                    checked_at = ?
                WHERE id = ?
            """.format(days_after), (
                actual_price,
                actual_return,
                datetime.now().isoformat(),
                prediction_id
            ))
            
            # 모든 기간 확인되었는지 체크
            cursor = await db.execute("""
                SELECT predicted_direction, expected_return,
                       actual_return_1d, actual_return_3d, actual_return_7d
                FROM predictions WHERE id = ?
            """, (prediction_id,))
            
            row = await cursor.fetchone()
            
            # 상태 업데이트
            if row[2] is not None:  # 1일 결과가 있으면
                predicted_up = row[0] == 'up'
                actual_up = row[2] > 0
                
                status = PredictionStatus.CORRECT if predicted_up == actual_up else PredictionStatus.INCORRECT
                
                await db.execute("""
                    UPDATE predictions SET status = ? WHERE id = ?
                """, (status, prediction_id))
            
            await db.commit()
            
        logger.info("prediction_result_updated",
                   prediction_id=prediction_id,
                   days_after=days_after,
                   actual_return=actual_return)
    
    async def calculate_performance_metrics(self, period: str = 'daily') -> PerformanceMetrics:
        """성과 지표 계산"""
        if not self._initialized:
            await self.initialize()
            
        # 기간 설정
        if period == 'daily':
            start_date = datetime.now() - timedelta(days=1)
        elif period == 'weekly':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'monthly':
            start_date = datetime.now() - timedelta(days=30)
        else:  # all-time
            start_date = datetime(2000, 1, 1)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 전체 예측 통계
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as correct,
                    SUM(CASE WHEN predicted_direction = 'up' THEN 1 ELSE 0 END) as bullish,
                    SUM(CASE WHEN predicted_direction = 'up' AND status = 'correct' THEN 1 ELSE 0 END) as bullish_correct,
                    SUM(CASE WHEN predicted_direction = 'down' THEN 1 ELSE 0 END) as bearish,
                    SUM(CASE WHEN predicted_direction = 'down' AND status = 'correct' THEN 1 ELSE 0 END) as bearish_correct
                FROM predictions
                WHERE prediction_date >= ? 
                AND status IN ('correct', 'incorrect')
            """, (start_date.isoformat(),))
            
            stats = await cursor.fetchone()
            
            # 신뢰도별 정확도
            confidence_stats = {}
            for conf_level, conf_range in [
                ('high', (0.7, 1.0)),
                ('medium', (0.5, 0.7)),
                ('low', (0.0, 0.5))
            ]:
                cursor = await db.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as correct
                    FROM predictions
                    WHERE prediction_date >= ?
                    AND confidence >= ? AND confidence < ?
                    AND status IN ('correct', 'incorrect')
                """, (start_date.isoformat(), conf_range[0], conf_range[1]))
                
                conf_stat = await cursor.fetchone()
                accuracy = conf_stat['correct'] / conf_stat['total'] if conf_stat['total'] > 0 else 0
                confidence_stats[conf_level] = accuracy
            
            # 섹터별 성과 (간단히 구현)
            sector_performance = {}  # TODO: 섹터별 분석 구현
            
        # 메트릭 생성
        metrics = PerformanceMetrics(
            period=period,
            total_predictions=stats['total'],
            correct_predictions=stats['correct'],
            accuracy_rate=stats['correct'] / stats['total'] if stats['total'] > 0 else 0,
            
            bullish_predictions=stats['bullish'],
            bullish_correct=stats['bullish_correct'],
            bullish_accuracy=stats['bullish_correct'] / stats['bullish'] if stats['bullish'] > 0 else 0,
            
            bearish_predictions=stats['bearish'],
            bearish_correct=stats['bearish_correct'],
            bearish_accuracy=stats['bearish_correct'] / stats['bearish'] if stats['bearish'] > 0 else 0,
            
            high_confidence_accuracy=confidence_stats['high'],
            medium_confidence_accuracy=confidence_stats['medium'],
            low_confidence_accuracy=confidence_stats['low'],
            
            paper_trading_return=0,  # TODO: paper trading 연동
            paper_trading_return_pct=0,
            benchmark_return=0,
            alpha=0,
            
            volatility=0,
            max_drawdown=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            
            sector_performance=sector_performance,
            last_updated=datetime.now()
        )
        
        # 메트릭 저장
        await self._save_metrics(metrics)
        
        return metrics
    
    async def _save_metrics(self, metrics: PerformanceMetrics):
        """성과 지표 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO performance_metrics (period, metrics)
                VALUES (?, ?)
            """, (metrics.period, metrics.json()))
            await db.commit()
    
    async def get_recent_predictions(self, 
                                   ticker: Optional[str] = None,
                                   limit: int = 100) -> List[Dict]:
        """최근 예측 조회"""
        if not self._initialized:
            await self.initialize()
            
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = """
                SELECT * FROM predictions 
                WHERE 1=1
            """
            params = []
            
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)
                
            query += " ORDER BY prediction_date DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
        return [dict(row) for row in rows]
    
    async def cleanup_old_predictions(self, days: int = 90):
        """오래된 예측 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM predictions
                WHERE prediction_date < ?
                AND status != 'pending'
            """, (cutoff_date.isoformat(),))
            
            await db.commit()
            
        logger.info("old_predictions_cleaned", cutoff_date=cutoff_date)
