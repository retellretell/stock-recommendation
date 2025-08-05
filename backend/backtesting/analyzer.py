"""
백테스팅 성과 분석기
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import aiosqlite

from .models import PerformanceMetrics
from .tracker import PredictionTracker
from .paper_trading import PaperTradingEngine

logger = structlog.get_logger()

class PerformanceAnalyzer:
    """성과 분석 및 리포트 생성"""
    
    def __init__(self, db_path: str = "backtesting.db"):
        self.db_path = db_path
        self.tracker = PredictionTracker(db_path)
        self.paper_trading = PaperTradingEngine(db_path)
        
    async def generate_report(self, 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict:
        """종합 성과 리포트 생성"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        logger.info("generating_performance_report", 
                   start_date=start_date, 
                   end_date=end_date)
        
        # 각 분석 수행
        prediction_analysis = await self._analyze_predictions(start_date, end_date)
        trading_analysis = await self._analyze_trading(start_date, end_date)
        risk_analysis = await self._analyze_risk(start_date, end_date)
        sector_analysis = await self._analyze_sectors(start_date, end_date)
        
        # 개선 제안 생성
        insights = self._generate_insights(
            prediction_analysis, 
            trading_analysis, 
            risk_analysis
        )
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'prediction_performance': prediction_analysis,
            'trading_performance': trading_analysis,
            'risk_metrics': risk_analysis,
            'sector_analysis': sector_analysis,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }
        
        return report
    
    async def _analyze_predictions(self, 
                                 start_date: datetime,
                                 end_date: datetime) -> Dict:
        """예측 정확도 분석"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 기본 통계
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as correct_predictions,
                    AVG(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as accuracy_rate,
                    AVG(confidence) as avg_confidence,
                    AVG(ABS(expected_return - actual_return_1d)) as avg_error_1d
                FROM predictions
                WHERE prediction_date BETWEEN ? AND ?
                AND status IN ('correct', 'incorrect')
            """, (start_date.isoformat(), end_date.isoformat()))
            
            basic_stats = dict(await cursor.fetchone())
            
            # 시간대별 정확도
            cursor = await db.execute("""
                SELECT 
                    strftime('%H', prediction_date) as hour,
                    COUNT(*) as predictions,
                    AVG(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as accuracy
                FROM predictions
                WHERE prediction_date BETWEEN ? AND ?
                AND status IN ('correct', 'incorrect')
                GROUP BY hour
                ORDER BY accuracy DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            hourly_accuracy = [dict(row) for row in await cursor.fetchall()]
            
            # 신뢰도별 정확도
            cursor = await db.execute("""
                SELECT 
                    CASE 
                        WHEN confidence >= 0.8 THEN 'very_high'
                        WHEN confidence >= 0.7 THEN 'high'
                        WHEN confidence >= 0.6 THEN 'medium'
                        WHEN confidence >= 0.5 THEN 'low'
                        ELSE 'very_low'
                    END as confidence_level,
                    COUNT(*) as predictions,
                    AVG(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as accuracy,
                    AVG(ABS(expected_return)) as avg_expected_return,
                    AVG(actual_return_1d) as avg_actual_return
                FROM predictions
                WHERE prediction_date BETWEEN ? AND ?
                AND status IN ('correct', 'incorrect')
                GROUP BY confidence_level
                ORDER BY confidence DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            confidence_analysis = [dict(row) for row in await cursor.fetchall()]
            
            # 예측 기간별 정확도
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as correct_1d,
                    SUM(CASE WHEN 
                        (predicted_direction = 'up' AND actual_return_3d > 0) OR
                        (predicted_direction = 'down' AND actual_return_3d < 0)
                        THEN 1 ELSE 0 END) as correct_3d,
                    SUM(CASE WHEN 
                        (predicted_direction = 'up' AND actual_return_7d > 0) OR
                        (predicted_direction = 'down' AND actual_return_7d < 0)
                        THEN 1 ELSE 0 END) as correct_7d
                FROM predictions
                WHERE prediction_date BETWEEN ? AND ?
                AND actual_return_7d IS NOT NULL
            """, (start_date.isoformat(), end_date.isoformat()))
            
            period_accuracy = dict(await cursor.fetchone())
            
        return {
            'summary': basic_stats,
            'hourly_accuracy': hourly_accuracy,
            'confidence_analysis': confidence_analysis,
            'period_accuracy': {
                '1_day': period_accuracy['correct_1d'] / period_accuracy['total'] if period_accuracy['total'] > 0 else 0,
                '3_days': period_accuracy['correct_3d'] / period_accuracy['total'] if period_accuracy['total'] > 0 else 0,
                '7_days': period_accuracy['correct_7d'] / period_accuracy['total'] if period_accuracy['total'] > 0 else 0
            },
            'best_prediction_hour': hourly_accuracy[0]['hour'] if hourly_accuracy else None,
            'optimal_confidence_threshold': self._find_optimal_confidence(confidence_analysis)
        }
    
    async def _analyze_trading(self, 
                             start_date: datetime,
                             end_date: datetime) -> Dict:
        """거래 성과 분석"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 거래 통계
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN action = 'buy' THEN 1 ELSE 0 END) as buy_trades,
                    SUM(CASE WHEN action = 'sell' THEN 1 ELSE 0 END) as sell_trades,
                    SUM(realized_pnl) as total_realized_pnl,
                    AVG(realized_pnl) as avg_pnl_per_trade,
                    SUM(commission) as total_commission
                FROM paper_trades
                WHERE trade_date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            trade_stats = dict(await cursor.fetchone())
            
            # 승률 계산
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as closed_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE NULL END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE NULL END) as avg_loss
                FROM paper_trades
                WHERE action = 'sell'
                AND trade_date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            win_stats = dict(await cursor.fetchone())
            
            # 포트폴리오 성과
            cursor = await db.execute("""
                SELECT 
                    MIN(total_value) as min_value,
                    MAX(total_value) as max_value,
                    AVG(total_value) as avg_value,
                    (SELECT total_value FROM portfolio_history WHERE date >= ? ORDER BY date ASC LIMIT 1) as start_value,
                    (SELECT total_value FROM portfolio_history WHERE date <= ? ORDER BY date DESC LIMIT 1) as end_value
                FROM portfolio_history
                WHERE date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat(),
                  start_date.isoformat(), end_date.isoformat()))
            
            portfolio_stats = dict(await cursor.fetchone())
            
            # 수익률 계산
            if portfolio_stats['start_value'] and portfolio_stats['end_value']:
                period_return = (portfolio_stats['end_value'] - portfolio_stats['start_value']) / portfolio_stats['start_value'] * 100
            else:
                period_return = 0
                
            # 일별 수익률
            cursor = await db.execute("""
                SELECT date, total_value, daily_return
                FROM portfolio_history
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date.isoformat(), end_date.isoformat()))
            
            daily_data = [dict(row) for row in await cursor.fetchall()]
            
        return {
            'trade_statistics': trade_stats,
            'win_statistics': {
                **win_stats,
                'win_rate': win_stats['winning_trades'] / win_stats['closed_trades'] if win_stats['closed_trades'] > 0 else 0,
                'profit_factor': abs(win_stats['avg_win'] / win_stats['avg_loss']) if win_stats['avg_loss'] else 0
            },
            'portfolio_performance': {
                **portfolio_stats,
                'period_return': period_return,
                'annualized_return': period_return * 365 / (end_date - start_date).days if (end_date - start_date).days > 0 else 0
            },
            'daily_returns': daily_data
        }
    
    async def _analyze_risk(self, 
                          start_date: datetime,
                          end_date: datetime) -> Dict:
        """리스크 분석"""
        # 일일 수익률 데이터 가져오기
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT daily_return
                FROM portfolio_history
                WHERE date BETWEEN ? AND ?
                AND daily_return IS NOT NULL
                ORDER BY date
            """, (start_date.isoformat(), end_date.isoformat()))
            
            returns = [row[0] / 100 for row in await cursor.fetchall()]  # 퍼센트를 소수로
            
        if len(returns) < 2:
            return {
                'volatility': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'var_95': 0,
                'cvar_95': 0
            }
            
        returns_array = np.array(returns)
        
        # 변동성 (연율화)
        volatility = np.std(returns_array) * np.sqrt(252)
        
        # 최대 낙폭
        cumulative_returns = (1 + returns_array).cumprod()
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 샤프 비율
        risk_free_rate = 0.03 / 252  # 일일 무위험 수익률
        excess_returns = returns_array - risk_free_rate
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
        
        # 소르티노 비율
        downside_returns = returns_array[returns_array < risk_free_rate]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino_ratio = np.mean(excess_returns) / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # VaR (Value at Risk) - 95% 신뢰수준
        var_95 = np.percentile(returns_array, 5)
        
        # CVaR (Conditional VaR)
        cvar_95 = np.mean(returns_array[returns_array <= var_95]) if len(returns_array[returns_array <= var_95]) > 0 else var_95
        
        return {
            'volatility': round(volatility * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'var_95': round(var_95 * 100, 2),
            'cvar_95': round(cvar_95 * 100, 2),
            'risk_adjusted_return': round(np.mean(returns_array) / volatility * np.sqrt(252), 2) if volatility > 0 else 0
        }
    
    async def _analyze_sectors(self, 
                             start_date: datetime,
                             end_date: datetime) -> Dict:
        """섹터별 성과 분석"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 섹터별 예측 정확도
            cursor = await db.execute("""
                SELECT 
                    s.sector,
                    COUNT(p.id) as predictions,
                    AVG(CASE WHEN p.status = 'correct' THEN 1 ELSE 0 END) as accuracy,
                    AVG(p.confidence) as avg_confidence,
                    AVG(p.actual_return_1d) as avg_return
                FROM predictions p
                JOIN stocks s ON p.ticker = s.ticker
                WHERE p.prediction_date BETWEEN ? AND ?
                AND p.status IN ('correct', 'incorrect')
                GROUP BY s.sector
                ORDER BY accuracy DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            sector_predictions = [dict(row) for row in await cursor.fetchall()]
            
            # 섹터별 거래 성과
            cursor = await db.execute("""
                SELECT 
                    s.sector,
                    COUNT(t.id) as trades,
                    SUM(t.realized_pnl) as total_pnl,
                    AVG(t.realized_pnl) as avg_pnl,
                    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades
                FROM paper_trades t
                JOIN stocks s ON t.ticker = s.ticker
                WHERE t.trade_date BETWEEN ? AND ?
                AND t.action = 'sell'
                GROUP BY s.sector
                ORDER BY total_pnl DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            sector_trades = [dict(row) for row in await cursor.fetchall()]
            
        # 섹터별 분석이 없는 경우 더미 데이터
        if not sector_predictions:
            sector_predictions = [{'sector': 'Unknown', 'predictions': 0, 'accuracy': 0, 'avg_confidence': 0, 'avg_return': 0}]
        if not sector_trades:
            sector_trades = [{'sector': 'Unknown', 'trades': 0, 'total_pnl': 0, 'avg_pnl': 0, 'winning_trades': 0}]
            
        return {
            'sector_predictions': sector_predictions,
            'sector_trades': sector_trades,
            'best_performing_sector': sector_trades[0]['sector'] if sector_trades else None,
            'most_accurate_sector': sector_predictions[0]['sector'] if sector_predictions else None
        }
    
    def _find_optimal_confidence(self, confidence_analysis: List[Dict]) -> float:
        """최적 신뢰도 임계값 찾기"""
        if not confidence_analysis:
            return 0.6
            
        # 정확도 * 예측 수로 가중치 계산
        best_score = 0
        optimal_threshold = 0.6
        
        thresholds = {'very_high': 0.8, 'high': 0.7, 'medium': 0.6, 'low': 0.5}
        
        for analysis in confidence_analysis:
            level = analysis['confidence_level']
            if level in thresholds:
                score = analysis['accuracy'] * np.log1p(analysis['predictions'])
                if score > best_score:
                    best_score = score
                    optimal_threshold = thresholds[level]
                    
        return optimal_threshold
    
    def _generate_insights(self, 
                         prediction_analysis: Dict,
                         trading_analysis: Dict,
                         risk_analysis: Dict) -> List[Dict]:
        """인사이트 및 개선 제안 생성"""
        insights = []
        
        # 예측 정확도 인사이트
        accuracy = prediction_analysis['summary']['accuracy_rate']
        if accuracy < 0.5:
            insights.append({
                'type': 'warning',
                'category': 'prediction',
                'message': f"예측 정확도가 {accuracy:.1%}로 낮습니다. 모델 재학습을 고려하세요.",
                'action': 'retrain_model'
            })
        elif accuracy > 0.6:
            insights.append({
                'type': 'success',
                'category': 'prediction',
                'message': f"예측 정확도가 {accuracy:.1%}로 양호합니다.",
                'action': None
            })
            
        # 최적 거래 시간
        if prediction_analysis['best_prediction_hour']:
            insights.append({
                'type': 'info',
                'category': 'timing',
                'message': f"가장 정확한 예측 시간은 {prediction_analysis['best_prediction_hour']}시입니다.",
                'action': 'adjust_trading_time'
            })
            
        # 신뢰도 임계값
        optimal_confidence = prediction_analysis['optimal_confidence_threshold']
        insights.append({
            'type': 'recommendation',
            'category': 'confidence',
            'message': f"최적 신뢰도 임계값은 {optimal_confidence:.1f}입니다.",
            'action': 'update_confidence_threshold'
        })
        
        # 승률 분석
        win_rate = trading_analysis['win_statistics']['win_rate']
        profit_factor = trading_analysis['win_statistics']['profit_factor']
        
        if win_rate < 0.4:
            insights.append({
                'type': 'warning',
                'category': 'trading',
                'message': f"승률이 {win_rate:.1%}로 낮습니다. 진입 전략을 재검토하세요.",
                'action': 'review_entry_strategy'
            })
        elif profit_factor > 1.5:
            insights.append({
                'type': 'success',
                'category': 'trading',
                'message': f"Profit Factor가 {profit_factor:.2f}로 우수합니다.",
                'action': None
            })
            
        # 리스크 분석
        sharpe = risk_analysis['sharpe_ratio']
        max_dd = risk_analysis['max_drawdown']
        
        if sharpe < 0.5:
            insights.append({
                'type': 'warning',
                'category': 'risk',
                'message': f"샤프 비율이 {sharpe:.2f}로 낮습니다. 리스크 대비 수익이 부족합니다.",
                'action': 'improve_risk_management'
            })
            
        if abs(max_dd) > 20:
            insights.append({
                'type': 'alert',
                'category': 'risk',
                'message': f"최대 낙폭이 {abs(max_dd):.1f}%로 높습니다. 포지션 크기를 줄이세요.",
                'action': 'reduce_position_size'
            })
            
        # 섹터 추천
        if 'best_performing_sector' in trading_analysis:
            insights.append({
                'type': 'recommendation',
                'category': 'sector',
                'message': f"가장 수익성이 높은 섹터는 {trading_analysis['best_performing_sector']}입니다.",
                'action': 'focus_on_sector'
            })
            
        return insights
    
    async def generate_comparison_report(self, 
                                       period1_start: datetime,
                                       period1_end: datetime,
                                       period2_start: datetime,
                                       period2_end: datetime) -> Dict:
        """기간별 비교 리포트"""
        # 각 기간의 리포트 생성
        report1 = await self.generate_report(period1_start, period1_end)
        report2 = await self.generate_report(period2_start, period2_end)
        
        # 비교 분석
        comparison = {
            'period1': {
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'metrics': self._extract_key_metrics(report1)
            },
            'period2': {
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'metrics': self._extract_key_metrics(report2)
            },
            'improvements': [],
            'deteriorations': []
        }
        
        # 개선/악화 항목 찾기
        metrics1 = comparison['period1']['metrics']
        metrics2 = comparison['period2']['metrics']
        
        for key in metrics1:
            if key in metrics2:
                diff = metrics2[key] - metrics1[key]
                diff_pct = diff / abs(metrics1[key]) * 100 if metrics1[key] != 0 else 0
                
                if abs(diff_pct) > 10:  # 10% 이상 변화
                    item = {
                        'metric': key,
                        'period1_value': metrics1[key],
                        'period2_value': metrics2[key],
                        'change': diff,
                        'change_pct': diff_pct
                    }
                    
                    if diff_pct > 0:
                        comparison['improvements'].append(item)
                    else:
                        comparison['deteriorations'].append(item)
                        
        return comparison
    
    def _extract_key_metrics(self, report: Dict) -> Dict:
        """리포트에서 핵심 지표 추출"""
        return {
            'prediction_accuracy': report['prediction_performance']['summary']['accuracy_rate'],
            'win_rate': report['trading_performance']['win_statistics']['win_rate'],
            'total_return': report['trading_performance']['portfolio_performance']['period_return'],
            'sharpe_ratio': report['risk_metrics']['sharpe_ratio'],
            'max_drawdown': report['risk_metrics']['max_drawdown'],
            'avg_confidence': report['prediction_performance']['summary']['avg_confidence']
        }
