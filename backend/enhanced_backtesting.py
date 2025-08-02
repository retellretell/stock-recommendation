"""
향상된 백테스팅 시스템
리스크 메트릭과 시장 상황별 분석 포함
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import structlog
from dataclasses import dataclass
import asyncio

logger = structlog.get_logger()

@dataclass
class BacktestResult:
    """백테스트 결과 데이터 클래스"""
    period: Dict[str, str]
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    var_95: float
    cvar_95: float
    
class EnhancedBacktester:
    """개선된 백테스팅 시스템"""
    
    def __init__(self):
        self.risk_free_rate = 0.03  # 3% 무위험 수익률
        self.trading_days_per_year = 252
        
    async def run_comprehensive_backtest(self, 
                                       start_date: str, 
                                       end_date: str,
                                       initial_capital: float = 10000000) -> Dict:
        """종합 백테스팅 실행"""
        try:
            logger.info("backtest_started", 
                       start_date=start_date, 
                       end_date=end_date,
                       initial_capital=initial_capital)
            
            # 시장 데이터 로드
            market_data = await self._load_market_data(start_date, end_date)
            
            # 예측 데이터 생성
            predictions = await self._generate_predictions(market_data)
            
            # 거래 시뮬레이션
            trades = self._simulate_trades(predictions, initial_capital)
            
            # 시장 상황별 분석
            market_conditions = await self._analyze_market_conditions(trades, market_data)
            
            # 리스크 메트릭 계산
            risk_metrics = self._calculate_risk_metrics(trades)
            
            # 드로다운 분석
            drawdown_analysis = self._analyze_drawdowns(trades)
            
            # 정확도 메트릭
            accuracy_metrics = self._calculate_accuracy_metrics(predictions, market_data)
            
            results = {
                'period': {
                    'start': start_date, 
                    'end': end_date,
                    'trading_days': len(market_data)
                },
                'overall_performance': {
                    'total_trades': len(trades),
                    'initial_capital': initial_capital,
                    'final_capital': trades[-1]['portfolio_value'] if trades else initial_capital,
                    'total_return': self._calculate_total_return(trades, initial_capital),
                    'annualized_return': self._calculate_annualized_return(trades, initial_capital),
                },
                'accuracy_metrics': accuracy_metrics,
                'risk_metrics': risk_metrics,
                'market_condition_analysis': market_conditions,
                'drawdown_analysis': drawdown_analysis,
                'trade_statistics': self._calculate_trade_statistics(trades),
                'monthly_returns': self._calculate_monthly_returns(trades)
            }
            
            logger.info("backtest_completed", total_trades=len(trades))
            
            return results
            
        except Exception as e:
            logger.error("backtest_error", error=str(e))
            raise
    
    async def _load_market_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """시장 데이터 로드 (실제로는 데이터베이스에서)"""
        # 더미 구현
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 영업일만
        
        # 시뮬레이션용 가격 데이터 생성
        np.random.seed(42)
        prices = [100]
        
        for _ in range(len(dates) - 1):
            # 랜덤 워크
            change = np.random.normal(0.0005, 0.02)  # 일 평균 0.05%, 표준편차 2%
            prices.append(prices[-1] * (1 + change))
        
        df = pd.DataFrame({
            'date': dates,
            'price': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        
        # 시장 상황 레이블 추가
        df['market_condition'] = self._label_market_conditions(df['price'])
        
        return df
    
    async def _generate_predictions(self, market_data: pd.DataFrame) -> List[Dict]:
        """예측 데이터 생성 (실제로는 모델 사용)"""
        predictions = []
        
        for i in range(20, len(market_data)):  # 20일 이후부터 예측
            # 간단한 모멘텀 기반 예측
            returns = market_data['price'].iloc[i-20:i].pct_change().dropna()
            momentum = returns.mean()
            volatility = returns.std()
            
            # 예측 확률 (모멘텀 기반)
            base_prob = 0.5 + momentum * 10  # 모멘텀에 따라 조정
            noise = np.random.normal(0, 0.1)  # 노이즈 추가
            probability = max(0.1, min(0.9, base_prob + noise))
            
            # 신뢰도 (변동성이 낮을수록 높음)
            confidence = max(0.3, 1 - volatility * 5)
            
            predictions.append({
                'date': market_data['date'].iloc[i],
                'price': market_data['price'].iloc[i],
                'probability': probability,
                'confidence': confidence,
                'actual_return': market_data['price'].iloc[i+1] / market_data['price'].iloc[i] - 1 if i < len(market_data) - 1 else 0
            })
        
        return predictions
    
    def _simulate_trades(self, predictions: List[Dict], initial_capital: float) -> List[Dict]:
        """거래 시뮬레이션"""
        trades = []
        capital = initial_capital
        position = 0  # 보유 주식 수
        
        for i, pred in enumerate(predictions[:-1]):  # 마지막 날 제외
            # 거래 신호
            if pred['probability'] > 0.65 and pred['confidence'] > 0.6:
                # 매수 신호
                if position == 0:  # 포지션이 없을 때만
                    shares = int(capital * 0.95 / pred['price'])  # 자금의 95% 사용
                    if shares > 0:
                        cost = shares * pred['price']
                        capital -= cost
                        position = shares
                        
                        trades.append({
                            'date': pred['date'],
                            'type': 'BUY',
                            'price': pred['price'],
                            'shares': shares,
                            'capital': capital,
                            'position': position,
                            'portfolio_value': capital + position * pred['price']
                        })
                        
            elif pred['probability'] < 0.35 and position > 0:
                # 매도 신호
                revenue = position * pred['price']
                capital += revenue
                
                trades.append({
                    'date': pred['date'],
                    'type': 'SELL',
                    'price': pred['price'],
                    'shares': position,
                    'capital': capital,
                    'position': 0,
                    'portfolio_value': capital,
                    'profit': revenue - trades[-1]['shares'] * trades[-1]['price'] if trades else 0
                })
                
                position = 0
            
            # 포지션 유지 (기록만)
            if i % 20 == 0:  # 20일마다 기록
                current_value = capital + position * pred['price']
                trades.append({
                    'date': pred['date'],
                    'type': 'HOLD',
                    'price': pred['price'],
                    'shares': 0,
                    'capital': capital,
                    'position': position,
                    'portfolio_value': current_value
                })
        
        return trades
    
    def _label_market_conditions(self, prices: pd.Series) -> pd.Series:
        """시장 상황 레이블링"""
        returns = prices.pct_change()
        rolling_mean = returns.rolling(window=20).mean()
        rolling_std = returns.rolling(window=20).std()
        
        conditions = []
        for i in range(len(prices)):
            if i < 20:
                conditions.append('unknown')
            elif rolling_mean.iloc[i] > 0.001 and rolling_std.iloc[i] < 0.02:
                conditions.append('bull')  # 상승장
            elif rolling_mean.iloc[i] < -0.001 and rolling_std.iloc[i] < 0.02:
                conditions.append('bear')  # 하락장
            elif rolling_std.iloc[i] > 0.025:
                conditions.append('volatile')  # 변동성 높음
            else:
                conditions.append('sideways')  # 횡보장
        
        return pd.Series(conditions)
    
    async def _analyze_market_conditions(self, trades: List[Dict], market_data: pd.DataFrame) -> Dict:
        """시장 상황별 성과 분석"""
        if not trades:
            return {}
        
        # 거래를 시장 상황별로 그룹화
        condition_results = {
            'bull': {'trades': 0, 'wins': 0, 'total_return': 0},
            'bear': {'trades': 0, 'wins': 0, 'total_return': 0},
            'sideways': {'trades': 0, 'wins': 0, 'total_return': 0},
            'volatile': {'trades': 0, 'wins': 0, 'total_return': 0}
        }
        
        for i in range(len(trades) - 1):
            if trades[i]['type'] == 'BUY' and trades[i+1]['type'] == 'SELL':
                # 매수-매도 쌍 찾기
                buy_date = trades[i]['date']
                sell_date = trades[i+1]['date']
                
                # 해당 기간의 주요 시장 상황
                mask = (market_data['date'] >= buy_date) & (market_data['date'] <= sell_date)
                conditions = market_data.loc[mask, 'market_condition'].value_counts()
                
                if not conditions.empty:
                    dominant_condition = conditions.idxmax()
                    
                    profit = trades[i+1].get('profit', 0)
                    return_pct = profit / (trades[i]['shares'] * trades[i]['price']) if trades[i]['shares'] > 0 else 0
                    
                    if dominant_condition in condition_results:
                        condition_results[dominant_condition]['trades'] += 1
                        if profit > 0:
                            condition_results[dominant_condition]['wins'] += 1
                        condition_results[dominant_condition]['total_return'] += return_pct
        
        # 결과 정리
        analysis = {}
        for condition, results in condition_results.items():
            if results['trades'] > 0:
                analysis[condition] = {
                    'total_trades': results['trades'],
                    'win_rate': results['wins'] / results['trades'],
                    'avg_return': results['total_return'] / results['trades'],
                    'total_return': results['total_return']
                }
            else:
                analysis[condition] = {
                    'total_trades': 0,
                    'win_rate': 0,
                    'avg_return': 0,
                    'total_return': 0
                }
        
        return analysis
    
    def _calculate_risk_metrics(self, trades: List[Dict]) -> Dict:
        """리스크 메트릭 계산"""
        if not trades:
            return {}
        
        # 일일 수익률 계산
        returns = []
        for i in range(1, len(trades)):
            if trades[i-1]['portfolio_value'] > 0:
                daily_return = trades[i]['portfolio_value'] / trades[i-1]['portfolio_value'] - 1
                returns.append(daily_return)
        
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        # 샤프 비율
        excess_returns = returns_array - self.risk_free_rate / self.trading_days_per_year
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(self.trading_days_per_year) if np.std(excess_returns) > 0 else 0
        
        # 소르티노 비율 (하방 리스크만 고려)
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino_ratio = np.mean(excess_returns) / downside_std * np.sqrt(self.trading_days_per_year) if downside_std > 0 else 0
        
        # 칼마 비율
        max_dd = self._calculate_max_drawdown(trades)
        annual_return = self._calculate_annualized_return(trades, trades[0]['portfolio_value'])
        calmar_ratio = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # VaR (Value at Risk) - 95% 신뢰수준
        var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0
        
        # CVaR (Conditional VaR)
        cvar_95 = np.mean(returns_array[returns_array <= var_95]) if len(returns_array[returns_array <= var_95]) > 0 else var_95
        
        return {
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'var_95': round(var_95 * 100, 2),  # 퍼센트로 변환
            'cvar_95': round(cvar_95 * 100, 2),
            'volatility': round(np.std(returns_array) * np.sqrt(self.trading_days_per_year) * 100, 2),
            'downside_volatility': round(downside_std * np.sqrt(self.trading_days_per_year) * 100, 2) if downside_std > 0 else 0
        }
    
    def _analyze_drawdowns(self, trades: List[Dict]) -> Dict:
        """드로다운 분석"""
        if not trades:
            return {}
        
        # 누적 최고값 추적
        peak = trades[0]['portfolio_value']
        drawdowns = []
        current_dd = 0
        dd_start = None
        
        for i, trade in enumerate(trades):
            value = trade['portfolio_value']
            
            if value > peak:
                if current_dd < 0:
                    # 드로다운 종료
                    drawdowns.append({
                        'start_date': dd_start,
                        'end_date': trade['date'],
                        'drawdown': current_dd,
                        'duration': i - drawdowns[-1]['start_idx'] if drawdowns else 0
                    })
                peak = value
                current_dd = 0
                dd_start = None
            else:
                dd = (value - peak) / peak
                if dd < current_dd:
                    current_dd = dd
                    if dd_start is None:
                        dd_start = trade['date']
        
        # 최대 드로다운
        max_dd = min([d['drawdown'] for d in drawdowns]) if drawdowns else 0
        
        # 평균 드로다운
        avg_dd = np.mean([d['drawdown'] for d in drawdowns]) if drawdowns else 0
        
        # 드로다운 지속 기간
        avg_duration = np.mean([d['duration'] for d in drawdowns]) if drawdowns else 0
        
        # 복구 시간 (평균)
        recovery_times = []
        for dd in drawdowns:
            if 'end_date' in dd and dd['end_date']:
                recovery_times.append(dd['duration'])
        
        avg_recovery = np.mean(recovery_times) if recovery_times else 0
        
        return {
            'max_drawdown': round(max_dd * 100, 2),
            'avg_drawdown': round(avg_dd * 100, 2),
            'total_drawdowns': len(drawdowns),
            'avg_duration_days': round(avg_duration, 1),
            'avg_recovery_days': round(avg_recovery, 1),
            'current_drawdown': round(current_dd * 100, 2),
            'drawdown_periods': drawdowns[:5]  # 상위 5개만
        }
    
    def _calculate_accuracy_metrics(self, predictions: List[Dict], market_data: pd.DataFrame) -> Dict:
        """예측 정확도 메트릭"""
        if not predictions:
            return {}
        
        correct_predictions = 0
        bullish_correct = 0
        bearish_correct = 0
        total_bullish = 0
        total_bearish = 0
        
        for pred in predictions:
            actual_direction = 1 if pred['actual_return'] > 0 else 0
            predicted_direction = 1 if pred['probability'] > 0.5 else 0
            
            if predicted_direction == actual_direction:
                correct_predictions += 1
                
            if predicted_direction == 1:
                total_bullish += 1
                if actual_direction == 1:
                    bullish_correct += 1
            else:
                total_bearish += 1
                if actual_direction == 0:
                    bearish_correct += 1
        
        total = len(predictions)
        
        return {
            'overall_accuracy': round(correct_predictions / total * 100, 1) if total > 0 else 0,
            'bullish_accuracy': round(bullish_correct / total_bullish * 100, 1) if total_bullish > 0 else 0,
            'bearish_accuracy': round(bearish_correct / total_bearish * 100, 1) if total_bearish > 0 else 0,
            'total_predictions': total,
            'bullish_predictions': total_bullish,
            'bearish_predictions': total_bearish,
            'directional_accuracy': round(correct_predictions / total * 100, 1) if total > 0 else 0
        }
    
    def _calculate_trade_statistics(self, trades: List[Dict]) -> Dict:
        """거래 통계"""
        if not trades:
            return {}
        
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        # 수익/손실 계산
        profits = []
        for i, sell in enumerate(sell_trades):
            if i < len(buy_trades):
                profit = sell.get('profit', 0)
                profits.append(profit)
        
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        return {
            'total_trades': len(buy_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(profits) * 100, 1) if profits else 0,
            'avg_win': round(np.mean(winning_trades), 0) if winning_trades else 0,
            'avg_loss': round(np.mean(losing_trades), 0) if losing_trades else 0,
            'profit_factor': round(sum(winning_trades) / abs(sum(losing_trades)), 2) if losing_trades else 0,
            'largest_win': round(max(winning_trades), 0) if winning_trades else 0,
            'largest_loss': round(min(losing_trades), 0) if losing_trades else 0,
            'avg_holding_days': self._calculate_avg_holding_period(trades)
        }
    
    def _calculate_monthly_returns(self, trades: List[Dict]) -> List[Dict]:
        """월별 수익률"""
        if not trades:
            return []
        
        # 월별로 그룹화
        monthly_data = {}
        
        for trade in trades:
            month_key = trade['date'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'start_value': trade['portfolio_value'],
                    'end_value': trade['portfolio_value']
                }
            else:
                monthly_data[month_key]['end_value'] = trade['portfolio_value']
        
        # 월별 수익률 계산
        monthly_returns = []
        for month, data in sorted(monthly_data.items()):
            if data['start_value'] > 0:
                monthly_return = (data['end_value'] - data['start_value']) / data['start_value'] * 100
                monthly_returns.append({
                    'month': month,
                    'return': round(monthly_return, 2),
                    'end_value': round(data['end_value'], 0)
                })
        
        return monthly_returns
    
    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """최대 드로다운 계산"""
        if not trades:
            return 0
        
        peak = trades[0]['portfolio_value']
        max_dd = 0
        
        for trade in trades:
            value = trade['portfolio_value']
            if value > peak:
                peak = value
            else:
                dd = (value - peak) / peak
                if dd < max_dd:
                    max_dd = dd
        
        return max_dd
    
    def _calculate_total_return(self, trades: List[Dict], initial_capital: float) -> float:
        """총 수익률"""
        if not trades:
            return 0
        
        final_value = trades[-1]['portfolio_value']
        return (final_value - initial_capital) / initial_capital * 100
    
    def _calculate_annualized_return(self, trades: List[Dict], initial_capital: float) -> float:
        """연율화 수익률"""
        if not trades or len(trades) < 2:
            return 0
        
        total_return = self._calculate_total_return(trades, initial_capital) / 100
        days = (trades[-1]['date'] - trades[0]['date']).days
        years = days / 365.25
        
        if years > 0:
            annualized = (1 + total_return) ** (1 / years) - 1
            return annualized * 100
        
        return 0
    
    def _calculate_avg_holding_period(self, trades: List[Dict]) -> float:
        """평균 보유 기간"""
        holding_periods = []
        
        for i in range(len(trades) - 1):
            if trades[i]['type'] == 'BUY' and trades[i+1]['type'] == 'SELL':
                days = (trades[i+1]['date'] - trades[i]['date']).days
                holding_periods.append(days)
        
        return round(np.mean(holding_periods), 1) if holding_periods else 0
