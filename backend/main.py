# AI 투자주치의 - 투자 습관 진단 및 코칭 서비스
# Enhanced Version for 미래에셋증권 AI Festival
# main.py

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import uuid

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== 상수 정의 =====
class Constants:
    """시스템 전체 상수"""
    # 미래에셋증권 연동
    MSTOCK_API_URL = "https://api.mstock.miraeasset.com/v1"
    MSTOCK_COMMISSION_RATE = 0.08  # 기본 수수료율 0.08%
    MSTOCK_DISCOUNT_RATE = 0.04    # 리밸런싱 실행 시 할인율 0.04%
    
    # HyperCLOVA X 설정
    HYPERCLOVAX_API_URL = "https://api.hyperclovax.com/v1"
    MAX_TOKENS = 500
    
    # 행동 분석 임계값
    BEHAVIOR_THRESHOLDS = {
        'high_turnover': 2.0,      # 평균 대비 2배
        'short_holding': 7,        # 7일 미만
        'high_volatility': 0.15,   # 15% 초과
        'sector_concentration': 0.3, # 30% 이상
        'loss_delay': 0.3,         # 30% 이상
        'fomo_threshold': 0.05,    # 5% 급등 후 매수
        'min_cash_ratio': 0.1      # 최소 현금 비중 10%
    }
    
    # KPI 목표치
    TARGET_KPI = {
        'avg_holding_period': 7,    # 7일 이상
        'monthly_turnover': 30,     # 30% 이하
        'win_rate': 60,            # 60% 이상
        'portfolio_volatility': 12, # 12% 이하
        'fomo_count': 5            # 월 5회 이하
    }

# ===== 데이터 모델 =====
@dataclass
class InvestmentBehavior:
    """투자 행동 패턴 데이터"""
    user_id: str
    analysis_date: datetime
    avg_holding_period: float      # 평균 보유기간 (일)
    turnover_rate: float          # 회전율
    win_loss_ratio: float         # 익절/손절 비율
    win_rate: float              # 승률
    loss_delay_rate: float       # 손실확정 지연율
    fomo_purchase_count: int     # FOMO 매수 횟수
    portfolio_volatility: float  # 포트폴리오 변동성
    sector_concentration: Dict[str, float]  # 섹터별 집중도
    total_trades: int           # 총 거래 횟수
    avg_trade_size: float      # 평균 거래 규모
    max_drawdown: float        # 최대 손실폭 (MDD)
    cash_ratio: float          # 현금 비중

    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        data = asdict(self)
        data['analysis_date'] = self.analysis_date.isoformat()
        return data

@dataclass
class CoachingAction:
    """코칭 액션"""
    action_id: str
    action_type: str  # 'rebalancing', 'warning', 'goal_setting', 'habit_correction'
    priority: str     # 'high', 'medium', 'low'
    title: str
    description: str
    recommendation: Dict[str, Any]
    expected_impact: Dict[str, float]
    mstock_executable: bool  # M-STOCK에서 실행 가능 여부

# ===== 투자자 성향 분류 =====
class InvestorType(Enum):
    SHORT_TERM_TRADER = "단타형"
    LOSS_AVERSE = "손실회피 과도형"
    CONFIRMATION_BIAS = "확증편향 주의"
    FOMO_PRONE = "FOMO 취약형"
    OVERCONFIDENT = "과신형"
    BALANCED = "균형형"
    CONSERVATIVE = "보수형"
    AGGRESSIVE = "공격형"

# ===== 행동 분석기 =====
class BehaviorAnalyzer:
    """투자 행동 패턴 분석기 - 행동경제학 이론 적용"""
    
    def __init__(self):
        self.thresholds = Constants.BEHAVIOR_THRESHOLDS
        self.nudge_strategies = {
            'loss_aversion': self._apply_loss_aversion_nudge,
            'mental_accounting': self._apply_mental_accounting_nudge,
            'anchoring_bias': self._apply_anchoring_bias_nudge,
            'herding_behavior': self._apply_herding_behavior_nudge
        }
    
    async def analyze_behavior(self, transactions: pd.DataFrame, 
                             market_data: Optional[pd.DataFrame] = None) -> InvestmentBehavior:
        """거래 데이터로부터 행동 패턴 분석"""
        user_id = transactions['user_id'].iloc[0]
        
        # 기본 메트릭 계산
        metrics = await self._calculate_basic_metrics(transactions)
        
        # 행동경제학 기반 추가 분석
        behavioral_metrics = await self._analyze_behavioral_biases(transactions, market_data)
        
        # 포트폴리오 리스크 분석
        risk_metrics = await self._analyze_portfolio_risk(transactions)
        
        return InvestmentBehavior(
            user_id=user_id,
            analysis_date=datetime.now(),
            avg_holding_period=metrics['avg_holding_period'],
            turnover_rate=metrics['turnover_rate'],
            win_loss_ratio=metrics['win_loss_ratio'],
            win_rate=metrics['win_rate'],
            loss_delay_rate=behavioral_metrics['loss_delay_rate'],
            fomo_purchase_count=behavioral_metrics['fomo_count'],
            portfolio_volatility=risk_metrics['volatility'],
            sector_concentration=risk_metrics['sector_concentration'],
            total_trades=metrics['total_trades'],
            avg_trade_size=metrics['avg_trade_size'],
            max_drawdown=risk_metrics['max_drawdown'],
            cash_ratio=risk_metrics['cash_ratio']
        )
    
    async def _calculate_basic_metrics(self, transactions: pd.DataFrame) -> Dict:
        """기본 투자 지표 계산"""
        # 평균 보유기간
        holding_periods = []
        for stock in transactions['stock_code'].unique():
            stock_trades = transactions[transactions['stock_code'] == stock].copy()
            stock_trades = stock_trades.sort_values('date')
            
            buy_trades = stock_trades[stock_trades['type'] == 'buy']
            sell_trades = stock_trades[stock_trades['type'] == 'sell']
            
            for i, (_, buy) in enumerate(buy_trades.iterrows()):
                if i < len(sell_trades):
                    sell = sell_trades.iloc[i]
                    period = (sell['date'] - buy['date']).days
                    holding_periods.append(period)
        
        avg_holding = np.mean(holding_periods) if holding_periods else 0
        
        # 회전율 계산
        monthly_turnover = transactions.groupby(pd.Grouper(key='date', freq='M'))['value'].sum()
        avg_portfolio_value = transactions.groupby(pd.Grouper(key='date', freq='M'))['portfolio_value'].mean()
        turnover_rate = (monthly_turnover / avg_portfolio_value * 100).mean()
        
        # 승률 계산
        trades_with_pnl = transactions[transactions['profit_loss'].notna()]
        winning_trades = trades_with_pnl[trades_with_pnl['profit_loss'] > 0]
        total_closed_trades = len(trades_with_pnl)
        win_rate = len(winning_trades) / max(total_closed_trades, 1) * 100
        
        # 익절/손절 비율
        avg_profit = winning_trades['profit_loss'].mean() if len(winning_trades) > 0 else 0
        losing_trades = trades_with_pnl[trades_with_pnl['profit_loss'] < 0]
        avg_loss = abs(losing_trades['profit_loss'].mean()) if len(losing_trades) > 0 else 1
        win_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        return {
            'avg_holding_period': avg_holding,
            'turnover_rate': turnover_rate,
            'win_loss_ratio': win_loss_ratio,
            'win_rate': win_rate,
            'total_trades': len(transactions),
            'avg_trade_size': transactions['value'].mean()
        }
    
    async def _analyze_behavioral_biases(self, transactions: pd.DataFrame, 
                                       market_data: Optional[pd.DataFrame]) -> Dict:
        """행동경제학적 편향 분석"""
        # FOMO (Fear Of Missing Out) 패턴 감지
        fomo_count = 0
        for _, trade in transactions[transactions['type'] == 'buy'].iterrows():
            if trade.get('price_change_before_buy', 0) > self.thresholds['fomo_threshold']:
                fomo_count += 1
        
        # 손실 확정 지연 (Loss Aversion)
        loss_holding_periods = []
        profit_holding_periods = []
        
        for stock in transactions['stock_code'].unique():
            stock_trades = transactions[transactions['stock_code'] == stock]
            for _, trade in stock_trades.iterrows():
                if trade['type'] == 'sell':
                    holding_period = trade.get('holding_period', 0)
                    if trade['profit_loss'] < 0:
                        loss_holding_periods.append(holding_period)
                    else:
                        profit_holding_periods.append(holding_period)
        
        avg_loss_holding = np.mean(loss_holding_periods) if loss_holding_periods else 0
        avg_profit_holding = np.mean(profit_holding_periods) if profit_holding_periods else 1
        loss_delay_rate = (avg_loss_holding - avg_profit_holding) / max(avg_profit_holding, 1)
        
        return {
            'fomo_count': fomo_count,
            'loss_delay_rate': max(loss_delay_rate, 0),
            'herding_score': await self._calculate_herding_score(transactions, market_data),
            'overconfidence_score': await self._calculate_overconfidence_score(transactions)
        }
    
    async def _analyze_portfolio_risk(self, transactions: pd.DataFrame) -> Dict:
        """포트폴리오 리스크 분석"""
        # 현재 포트폴리오 구성
        latest_date = transactions['date'].max()
        current_portfolio = transactions[transactions['date'] == latest_date]
        
        # 섹터 집중도
        sector_values = current_portfolio.groupby('sector')['value'].sum()
        total_value = sector_values.sum()
        sector_concentration = {
            sector: value/total_value 
            for sector, value in sector_values.items()
        }
        
        # 변동성 계산
        daily_returns = transactions.groupby('date')['daily_return'].mean()
        volatility = daily_returns.std() * np.sqrt(252) * 100  # 연율화
        
        # MDD 계산
        cumulative_returns = (1 + daily_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100
        
        # 현금 비중
        cash_value = current_portfolio[current_portfolio['asset_type'] == 'cash']['value'].sum()
        cash_ratio = cash_value / total_value if total_value > 0 else 0
        
        return {
            'volatility': volatility,
            'sector_concentration': sector_concentration,
            'max_drawdown': max_drawdown,
            'cash_ratio': cash_ratio
        }
    
    async def _calculate_herding_score(self, transactions: pd.DataFrame, 
                                     market_data: Optional[pd.DataFrame]) -> float:
        """군집 행동 점수 계산"""
        # 시장 인기 종목 매수 비율로 계산
        if market_data is None:
            return 0.0
        
        popular_stocks = market_data.nlargest(10, 'trading_volume')['stock_code'].tolist()
        user_stocks = transactions['stock_code'].unique()
        
        overlap = len(set(user_stocks) & set(popular_stocks))
        return overlap / len(user_stocks) if len(user_stocks) > 0 else 0
    
    async def _calculate_overconfidence_score(self, transactions: pd.DataFrame) -> float:
        """과신 성향 점수 계산"""
        # 거래 빈도와 포지션 크기로 계산
        avg_position_size = transactions.groupby('stock_code')['value'].mean().mean()
        total_portfolio_value = transactions['portfolio_value'].iloc[-1]
        
        position_concentration = avg_position_size / total_portfolio_value
        trade_frequency = len(transactions) / 30  # 일평균 거래 횟수
        
        return min((position_concentration * 0.5 + trade_frequency * 0.5), 1.0)
    
    def _apply_loss_aversion_nudge(self, behavior: InvestmentBehavior) -> str:
        """손실 회피 편향에 대한 넛지"""
        return "손실을 확정하는 것이 더 큰 손실을 막는 첫걸음입니다. 작은 손실은 큰 수익의 기회비용입니다."
    
    def _apply_mental_accounting_nudge(self, behavior: InvestmentBehavior) -> str:
        """심적 회계 편향에 대한 넛지"""
        return "모든 투자금은 하나의 통합된 자산입니다. 개별 종목의 손익보다 전체 포트폴리오 관점에서 판단하세요."
    
    def _apply_anchoring_bias_nudge(self, behavior: InvestmentBehavior) -> str:
        """기준점 편향에 대한 넛지"""
        return "매수가격은 과거일 뿐입니다. 현재 시점에서 '새로 산다면' 이 가격에 살 것인지 생각해보세요."
    
    def _apply_herding_behavior_nudge(self, behavior: InvestmentBehavior) -> str:
        """군집 행동에 대한 넛지"""
        return "남들이 모두 사는 주식이 항상 좋은 것은 아닙니다. 자신만의 투자 원칙을 지키세요."
    
    def classify_investor_type(self, behavior: InvestmentBehavior) -> List[InvestorType]:
        """투자자 성향 분류 - 복수 성향 허용"""
        types = []
        
        # 단타형
        if behavior.avg_holding_period < self.thresholds['short_holding']:
            types.append(InvestorType.SHORT_TERM_TRADER)
        
        # 손실회피 과도형
        if behavior.loss_delay_rate > self.thresholds['loss_delay']:
            types.append(InvestorType.LOSS_AVERSE)
        
        # FOMO 취약형
        if behavior.fomo_purchase_count > Constants.TARGET_KPI['fomo_count']:
            types.append(InvestorType.FOMO_PRONE)
        
        # 과신형
        if behavior.turnover_rate > 100 and behavior.avg_trade_size > behavior.cash_ratio * 2:
            types.append(InvestorType.OVERCONFIDENT)
        
        # 보수형
        if behavior.cash_ratio > 0.3 and behavior.portfolio_volatility < 10:
            types.append(InvestorType.CONSERVATIVE)
        
        # 공격형
        if behavior.portfolio_volatility > 20 and behavior.cash_ratio < 0.05:
            types.append(InvestorType.AGGRESSIVE)
        
        # 기본값
        if not types:
            types.append(InvestorType.BALANCED)
        
        return types

# ===== 정책 기반 룰 엔진 =====
class RuleEngine:
    """정책 기반 룰 엔진 - 미래에셋증권 투자 원칙 반영"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.rule_history = {}  # 룰 실행 이력
    
    def _initialize_rules(self) -> List[Dict]:
        """룰 정의 - 우선순위 기반"""
        return [
            # 긴급 룰 (High Priority)
            {
                'id': 'R-001',
                'name': '과도한 회전율 경고',
                'priority': 'high',
                'condition': lambda b: b.turnover_rate > b.avg_holding_period * 2,
                'action_type': 'warning',
                'recommendation': {
                    'cash_ratio': 0.2,
                    'trading_suspension_days': 3
                },
                'message_template': "회전율이 지난 90일 평균 대비 {rate:.1f}배 높아졌습니다. 감정적 매매를 자제하세요.",
                'expected_impact': {
                    'turnover_reduction': -30,
                    'cost_saving': 0.04  # 수수료 절감
                },
                'mstock_executable': True
            },
            {
                'id': 'R-002',
                'name': '손실 확대 패턴 감지',
                'priority': 'high',
                'condition': lambda b: b.avg_holding_period < 7 and b.win_rate < 40,
                'action_type': 'goal_setting',
                'recommendation': {
                    'min_holding_days': 7,
                    'stop_loss': -0.07,
                    'take_profit': 0.15
                },
                'message_template': "평균 보유기간 {days:.1f}일은 목표 대비 너무 짧습니다. 단기 매매를 줄이세요.",
                'expected_impact': {
                    'holding_period_increase': 50,
                    'win_rate_improvement': 20
                },
                'mstock_executable': True
            },
            {
                'id': 'R-003',
                'name': '포트폴리오 변동성 과다',
                'priority': 'high',
                'condition': lambda b: b.portfolio_volatility > Constants.TARGET_KPI['portfolio_volatility'] * 1.5,
                'action_type': 'rebalancing',
                'recommendation': {
                    'reduce_high_vol_stocks': True,
                    'increase_defensive_sectors': True,
                    'target_volatility': Constants.TARGET_KPI['portfolio_volatility']
                },
                'message_template': "현재 변동성 {vol:.1f}%가 목표 {target}%보다 높습니다. 리스크 관리가 필요합니다.",
                'expected_impact': {
                    'volatility_reduction': -25,
                    'max_drawdown_improvement': -20
                },
                'mstock_executable': True
            },
            
            # 중간 우선순위 룰 (Medium Priority)
            {
                'id': 'R-004',
                'name': '섹터 집중 리스크',
                'priority': 'medium',
                'condition': lambda b: any(conc > Constants.BEHAVIOR_THRESHOLDS['sector_concentration'] 
                                         for conc in b.sector_concentration.values()),
                'action_type': 'rebalancing',
                'recommendation': {
                    'max_sector_weight': 0.3,
                    'diversification_targets': ['금융', '헬스케어', '소비재']
                },
                'message_template': "특정 섹터 집중도가 {conc:.0%}로 과도합니다. 분산 투자를 고려하세요.",
                'expected_impact': {
                    'risk_reduction': -15,
                    'stability_improvement': 20
                },
                'mstock_executable': True
            },
            {
                'id': 'R-005',
                'name': 'FOMO 매수 패턴',
                'priority': 'medium',
                'condition': lambda b: b.fomo_purchase_count > Constants.TARGET_KPI['fomo_count'],
                'action_type': 'habit_correction',
                'recommendation': {
                    'cooling_period': 24,  # 24시간 숙려 기간
                    'price_alert_threshold': 0.03  # 3% 이상 급등 시 경고
                },
                'message_template': "급등 후 매수가 {count}회 발생했습니다. 추격 매수를 자제하세요.",
                'expected_impact': {
                    'fomo_reduction': -50,
                    'entry_price_improvement': 3
                },
                'mstock_executable': False
            },
            
            # 낮은 우선순위 룰 (Low Priority)
            {
                'id': 'R-006',
                'name': '현금 비중 부족',
                'priority': 'low',
                'condition': lambda b: b.cash_ratio < Constants.BEHAVIOR_THRESHOLDS['min_cash_ratio'],
                'action_type': 'rebalancing',
                'recommendation': {
                    'target_cash_ratio': 0.15,
                    'sell_overweight_positions': True
                },
                'message_template': "현금 비중 {cash:.0%}는 기회 포착에 불리합니다. 유동성을 확보하세요.",
                'expected_impact': {
                    'opportunity_capture': 30,
                    'stress_reduction': 25
                },
                'mstock_executable': True
            }
        ]
    
    async def evaluate_rules(self, behavior: InvestmentBehavior, 
                           user_context: Optional[Dict] = None) -> List[CoachingAction]:
        """행동 패턴에 대한 룰 평가 - 우선순위 기반"""
        triggered_actions = []
        
        # 우선순위별로 룰 평가
        for priority in ['high', 'medium', 'low']:
            priority_rules = [r for r in self.rules if r['priority'] == priority]
            
            for rule in priority_rules:
                if rule['condition'](behavior):
                    # 룰 실행 이력 확인 (중복 방지)
                    rule_key = f"{behavior.user_id}_{rule['id']}"
                    last_triggered = self.rule_history.get(rule_key)
                    
                    if last_triggered is None or (datetime.now() - last_triggered).days > 7:
                        action = await self._create_coaching_action(rule, behavior)
                        triggered_actions.append(action)
                        self.rule_history[rule_key] = datetime.now()
                        
                        # High priority는 최대 2개까지만
                        if priority == 'high' and len([a for a in triggered_actions 
                                                      if a.priority == 'high']) >= 2:
                            break
        
        return triggered_actions
    
    async def _create_coaching_action(self, rule: Dict, behavior: InvestmentBehavior) -> CoachingAction:
        """룰로부터 코칭 액션 생성"""
        # 메시지 포맷팅
        message_params = {
            'rate': behavior.turnover_rate / 100,
            'days': behavior.avg_holding_period,
            'vol': behavior.portfolio_volatility,
            'target': Constants.TARGET_KPI['portfolio_volatility'],
            'conc': max(behavior.sector_concentration.values()) if behavior.sector_concentration else 0,
            'count': behavior.fomo_purchase_count,
            'cash': behavior.cash_ratio
        }
        
        description = rule['message_template'].format(**message_params)
        
        return CoachingAction(
            action_id=f"{rule['id']}_{uuid.uuid4().hex[:8]}",
            action_type=rule['action_type'],
            priority=rule['priority'],
            title=rule['name'],
            description=description,
            recommendation=rule['recommendation'],
            expected_impact=rule['expected_impact'],
            mstock_executable=rule['mstock_executable']
        )

# ===== HyperCLOVA X 통합 =====
class HyperClovaXClient:
    """HyperCLOVA X API 클라이언트"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = Constants.HYPERCLOVAX_API_URL
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """프롬프트 템플릿 로드"""
        return {
            'behavior_summary': """
당신은 투자 행동 분석 전문가입니다. 다음 투자자의 행동 데이터를 분석하여 
친근하고 이해하기 쉬운 요약을 작성해주세요.

투자자 데이터:
- 평균 보유기간: {avg_holding}일
- 월 회전율: {turnover}%
- 승률: {win_rate}%
- 포트폴리오 변동성: {volatility}%
- 투자 성향: {investor_types}

핵심 문제점과 개선 방향을 2-3문장으로 요약해주세요.
""",
            'coaching_message': """
당신은 따뜻하고 전문적인 투자 코치입니다. 다음 상황에 대해 
동기부여가 되고 실천 가능한 조언을 해주세요.

상황: {situation}
권장 조치: {recommendation}
예상 효과: {expected_impact}

구체적이고 긍정적인 톤으로 150자 이내로 작성해주세요.
""",
            'rebalancing_explanation': """
포트폴리오 리밸런싱 제안을 쉽게 설명해주세요.

현재 포트폴리오: {current_portfolio}
제안 포트폴리오: {target_portfolio}
주요 변경사항: {changes}

왜 이런 변경이 필요한지, 어떤 효과가 있을지 설명해주세요.
"""
        }
    
    async def generate_behavior_summary(self, behavior: InvestmentBehavior, 
                                      investor_types: List[InvestorType]) -> str:
        """행동 패턴 요약 생성"""
        prompt = self.prompt_templates['behavior_summary'].format(
            avg_holding=behavior.avg_holding_period,
            turnover=behavior.turnover_rate,
            win_rate=behavior.win_rate,
            volatility=behavior.portfolio_volatility,
            investor_types=', '.join([t.value for t in investor_types])
        )
        
        # 실제 API 호출 시뮬레이션
        # response = await self._call_api(prompt)
        
        # 데모용 응답
        return f"""
최근 분석 결과, 평균 보유기간이 {behavior.avg_holding_period:.1f}일로 단기 매매 성향이 강하시네요. 
회전율 {behavior.turnover_rate:.0f}%는 평균보다 높아 거래 비용이 수익을 갉아먹고 있습니다. 
차분한 투자로 연 {behavior.turnover_rate * 0.08:.1f}% 추가 수익이 가능합니다!
"""
    
    async def generate_coaching_message(self, action: CoachingAction) -> str:
        """개인화된 코칭 메시지 생성"""
        prompt = self.prompt_templates['coaching_message'].format(
            situation=action.description,
            recommendation=json.dumps(action.recommendation, ensure_ascii=False),
            expected_impact=json.dumps(action.expected_impact, ensure_ascii=False)
        )
        
        # 데모용 응답
        impact_str = f"{list(action.expected_impact.values())[0]:+.0f}%"
        return f"""
{action.description} 
제안드린 방법을 실천하시면 {impact_str}의 개선이 예상됩니다. 
작은 변화가 큰 성과로 이어집니다. 함께 해보시죠! 💪"""
    
    async def generate_rebalancing_explanation(self, current: Dict, target: Dict, changes: List[Dict]) -> str:
        """리밸런싱 설명 생성"""
        prompt = self.prompt_templates['rebalancing_explanation'].format(
            current_portfolio=json.dumps(current, ensure_ascii=False),
            target_portfolio=json.dumps(target, ensure_ascii=False),
            changes=json.dumps(changes, ensure_ascii=False)
        )
        
        # 데모용 응답
        return """
포트폴리오 균형을 맞추는 것은 자전거 균형을 잡는 것과 같습니다. 
IT 섹터가 45%로 한쪽으로 기울어져 있어, 30%로 조정하면 더 안정적인 주행이 가능합니다. 
분산투자로 리스크는 줄이고 수익 기회는 넓혀보세요!
"""
    
    async def _call_api(self, prompt: str) -> str:
        """실제 API 호출 (구현 시)"""
        # headers = {"Authorization": f"Bearer {self.api_key}"}
        # data = {
        #     "prompt": prompt,
        #     "max_tokens": Constants.MAX_TOKENS,
        #     "temperature": 0.7
        # }
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(self.api_url, headers=headers, json=data)
        #     return response.json()["generated_text"]
        pass

# ===== 코칭 오케스트레이터 =====
class CoachingOrchestrator:
    """AI 코칭 통합 관리 - 미래에셋증권 시너지 극대화"""
    
    def __init__(self, llm_client: Optional[HyperClovaXClient] = None):
        self.behavior_analyzer = BehaviorAnalyzer()
        self.rule_engine = RuleEngine()
        self.llm_client = llm_client or HyperClovaXClient(api_key="demo")
        self.rebalancing_engine = RebalancingEngine()
        self.gamification_engine = GamificationEngine()
        self.mstock_integration = MStockIntegration()
    
    async def generate_comprehensive_report(self, user_id: str, 
                                          transactions: pd.DataFrame,
                                          market_data: Optional[pd.DataFrame] = None) -> Dict:
        """종합 투자 진단 리포트 생성"""
        logger.info(f"Generating comprehensive report for user {user_id}")
        
        # 1. 행동 패턴 분석
        behavior = await self.behavior_analyzer.analyze_behavior(transactions, market_data)
        
        # 2. 투자자 성향 분류
        investor_types = self.behavior_analyzer.classify_investor_type(behavior)
        
        # 3. 룰 엔진 평가
        coaching_actions = await self.rule_engine.evaluate_rules(behavior)
        
        # 4. AI 메시지 생성
        behavior_summary = await self.llm_client.generate_behavior_summary(behavior, investor_types)
        coaching_messages = []
        for action in coaching_actions[:3]:  # 상위 3개 액션
            message = await self.llm_client.generate_coaching_message(action)
            coaching_messages.append(message)
        
        # 5. 리밸런싱 계획 (필요시)
        rebalancing_plan = None
        if any(action.action_type == 'rebalancing' for action in coaching_actions):
            current_portfolio = self._extract_current_portfolio(transactions)
            rebalancing_plan = await self.rebalancing_engine.generate_rebalancing_plan(
                current_portfolio, behavior
            )
        
        # 6. 게이미피케이션 요소
        badges = await self.gamification_engine.check_achievements(behavior, transactions)
        streak_info = await self.gamification_engine.calculate_streaks(user_id, behavior)
        
        # 7. 개선 목표 생성
        improvement_goals = self._generate_improvement_goals(behavior)
        
        # 8. M-STOCK 실행 가능 액션
        executable_actions = [
            action for action in coaching_actions 
            if action.mstock_executable
        ]
        
        # 9. 예상 효과 계산
        expected_improvements = self._calculate_expected_improvements(
            behavior, coaching_actions, rebalancing_plan
        )
        
        report = {
            'report_id': str(uuid.uuid4()),
            'user_id': user_id,
            'analysis_date': datetime.now().isoformat(),
            'behavior_analysis': behavior.to_dict(),
            'investor_types': [t.value for t in investor_types],
            'behavior_summary': behavior_summary,
            'coaching_actions': [
                {
                    'action_id': action.action_id,
                    'type': action.action_type,
                    'priority': action.priority,
                    'title': action.title,
                    'description': action.description,
                    'recommendation': action.recommendation,
                    'expected_impact': action.expected_impact,
                    'mstock_executable': action.mstock_executable,
                    'coaching_message': coaching_messages[i] if i < len(coaching_messages) else None
                }
                for i, action in enumerate(coaching_actions)
            ],
            'rebalancing_plan': rebalancing_plan,
            'gamification': {
                'new_badges': badges,
                'streaks': streak_info,
                'level': await self.gamification_engine.calculate_level(user_id),
                'points': await self.gamification_engine.get_points(user_id)
            },
            'improvement_goals': improvement_goals,
            'mstock_integration': {
                'executable_actions': len(executable_actions),
                'estimated_commission_savings': self._estimate_commission_savings(behavior),
                'one_click_actions': [
                    {
                        'action_id': action.action_id,
                        'title': action.title,
                        'mstock_deep_link': self.mstock_integration.generate_deep_link(action)
                    }
                    for action in executable_actions
                ]
            },
            'expected_improvements': expected_improvements,
            'next_review_date': (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        logger.info(f"Report generated successfully for user {user_id}")
        return report
    
    def _extract_current_portfolio(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """현재 포트폴리오 추출"""
        latest_date = transactions['date'].max()
        return transactions[transactions['date'] == latest_date].copy()
    
    def _generate_improvement_goals(self, behavior: InvestmentBehavior) -> Dict:
        """개선 목표 생성"""
        goals = {}
        targets = Constants.TARGET_KPI
        
        # 보유기간 목표
        if behavior.avg_holding_period < targets['avg_holding_period']:
            goals['holding_period'] = {
                'current': behavior.avg_holding_period,
                'target': targets['avg_holding_period'],
                'improvement_needed': '+{:.0f}%'.format(
                    (targets['avg_holding_period'] - behavior.avg_holding_period) / 
                    behavior.avg_holding_period * 100
                ),
                'deadline': (datetime.now() + timedelta(days=30)).isoformat()
            }
        
        # 회전율 목표
        if behavior.turnover_rate > targets['monthly_turnover']:
            goals['turnover_rate'] = {
                'current': behavior.turnover_rate,
                'target': targets['monthly_turnover'],
                'improvement_needed': '-{:.0f}%'.format(
                    (behavior.turnover_rate - targets['monthly_turnover']) / 
                    behavior.turnover_rate * 100
                ),
                'deadline': (datetime.now() + timedelta(days=30)).isoformat()
            }
        
        # 승률 목표
        if behavior.win_rate < targets['win_rate']:
            goals['win_rate'] = {
                'current': behavior.win_rate,
                'target': targets['win_rate'],
                'improvement_needed': '+{:.0f}%p'.format(
                    targets['win_rate'] - behavior.win_rate
                ),
                'deadline': (datetime.now() + timedelta(days=60)).isoformat()
            }
        
        return goals
    
    def _estimate_commission_savings(self, behavior: InvestmentBehavior) -> Dict:
        """수수료 절감 효과 추정"""
        current_commission = behavior.turnover_rate * behavior.avg_trade_size * Constants.MSTOCK_COMMISSION_RATE / 100
        
        # 리밸런싱 실행 시 할인
        discounted_commission = current_commission * (Constants.MSTOCK_DISCOUNT_RATE / Constants.MSTOCK_COMMISSION_RATE)
        
        # 행동 개선으로 인한 추가 절감
        improved_turnover = behavior.turnover_rate * 0.7  # 30% 개선 가정
        improved_commission = improved_turnover * behavior.avg_trade_size * Constants.MSTOCK_DISCOUNT_RATE / 100
        
        return {
            'current_monthly_commission': current_commission,
            'with_discount': discounted_commission,
            'with_improvement': improved_commission,
            'total_annual_savings': (current_commission - improved_commission) * 12,
            'savings_percentage': ((current_commission - improved_commission) / current_commission * 100)
        }
    
    def _calculate_expected_improvements(self, behavior: InvestmentBehavior, 
                                       actions: List[CoachingAction],
                                       rebalancing_plan: Optional[Dict]) -> Dict:
        """종합 개선 효과 예측"""
        improvements = {
            'behavior_metrics': {},
            'financial_impact': {},
            'risk_reduction': {}
        }
        
        # 행동 지표 개선
        for action in actions:
            for metric, improvement in action.expected_impact.items():
                if metric not in improvements['behavior_metrics']:
                    improvements['behavior_metrics'][metric] = 0
                improvements['behavior_metrics'][metric] += improvement
        
        # 재무적 영향
        commission_savings = self._estimate_commission_savings(behavior)
        improvements['financial_impact'] = {
            'commission_savings_annual': commission_savings['total_annual_savings'],
            'improved_win_rate_impact': behavior.avg_trade_size * 0.05,  # 5% 개선 가정
            'opportunity_cost_reduction': behavior.avg_trade_size * 0.03  # 3% 기회비용 절감
        }
        
        # 리스크 감소
        if rebalancing_plan:
            improvements['risk_reduction'] = {
                'volatility_reduction': rebalancing_plan.get('expected_volatility_reduction', -15),
                'max_drawdown_improvement': rebalancing_plan.get('expected_mdd_improvement', -20),
                'sector_concentration_improvement': -25
            }
        
        # 종합 점수 (100점 만점)
        current_score = self._calculate_investment_score(behavior)
        expected_score = current_score + sum(improvements['behavior_metrics'].values()) / len(improvements['behavior_metrics'])
        improvements['overall_score'] = {
            'current': current_score,
            'expected': min(expected_score, 100),
            'improvement': expected_score - current_score
        }
        
        return improvements
    
    def _calculate_investment_score(self, behavior: InvestmentBehavior) -> float:
        """투자 점수 계산 (100점 만점)"""
        scores = {
            'holding_period': min(behavior.avg_holding_period / Constants.TARGET_KPI['avg_holding_period'] * 100, 100),
            'turnover': max(100 - behavior.turnover_rate / Constants.TARGET_KPI['monthly_turnover'] * 50, 0),
            'win_rate': behavior.win_rate / Constants.TARGET_KPI['win_rate'] * 100,
            'volatility': max(100 - behavior.portfolio_volatility / Constants.TARGET_KPI['portfolio_volatility'] * 50, 0),
            'fomo_control': max(100 - behavior.fomo_purchase_count / Constants.TARGET_KPI['fomo_count'] * 50, 0)
        }
        
        weights = {
            'holding_period': 0.2,
            'turnover': 0.2,
            'win_rate': 0.3,
            'volatility': 0.2,
            'fomo_control': 0.1
        }
        
        total_score = sum(scores[key] * weights[key] for key in scores)
        return round(total_score, 1)

# ===== 리밸런싱 엔진 =====
class RebalancingEngine:
    """포트폴리오 리밸런싱 엔진 - 미래에셋증권 투자 철학 반영"""
    
    def __init__(self):
        self.risk_limits = {
            'max_sector_concentration': 0.3,
            'max_single_stock': 0.1,
            'target_volatility': 0.12,
            'min_cash_ratio': 0.1,
            'max_correlation': 0.7
        }
        self.sector_recommendations = {
            'defensive': ['금융', '통신', '유틸리티'],
            'growth': ['IT', '바이오', '신재생에너지'],
            'cyclical': ['산업재', '소비재', '화학']
        }
    
    async def generate_rebalancing_plan(self, portfolio: pd.DataFrame, 
                                       behavior: InvestmentBehavior) -> Dict:
        """리밸런싱 계획 생성"""
        current_positions = self._analyze_current_portfolio(portfolio)
        risk_assessment = self._assess_portfolio_risk(portfolio, behavior)
        
        # 목표 포트폴리오 계산
        target_positions = await self._optimize_portfolio(
            current_positions, risk_assessment, behavior
        )
        
        # 필요한 거래 계산
        trades = self._calculate_required_trades(current_positions, target_positions)
        
        # 실행 계획
        execution_plan = self._create_execution_plan(trades, portfolio)
        
        return {
            'plan_id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat(),
            'current_portfolio': current_positions,
            'target_portfolio': target_positions,
            'risk_assessment': risk_assessment,
            'required_trades': trades,
            'execution_plan': execution_plan,
            'expected_results': {
                'volatility_reduction': -15,
                'sector_balance_improvement': 25,
                'risk_score_improvement': -20,
                'expected_mdd_improvement': -10
            },
            'mstock_executable': True,
            'estimated_cost': self._estimate_rebalancing_cost(trades),
            'implementation_timeline': '3-5 영업일'
        }
    
    def _analyze_current_portfolio(self, portfolio: pd.DataFrame) -> Dict:
        """현재 포트폴리오 분석"""
        total_value = portfolio['value'].sum()
        
        positions = {}
        for _, row in portfolio.iterrows():
            positions[row['stock_code']] = {
                'value': row['value'],
                'weight': row['value'] / total_value,
                'sector': row['sector'],
                'shares': row['shares'],
                'avg_price': row['avg_price'],
                'current_price': row['current_price'],
                'unrealized_pnl': (row['current_price'] - row['avg_price']) * row['shares'],
                'pnl_percent': (row['current_price'] / row['avg_price'] - 1) * 100
            }
        
        # 섹터별 집계
        sector_weights = {}
        for stock, data in positions.items():
            sector = data['sector']
            if sector not in sector_weights:
                sector_weights[sector] = 0
            sector_weights[sector] += data['weight']
        
        return {
            'positions': positions,
            'sector_weights': sector_weights,
            'total_value': total_value,
            'stock_count': len(positions),
            'cash_value': portfolio[portfolio['asset_type'] == 'cash']['value'].sum() if 'asset_type' in portfolio else 0
        }
    
    def _assess_portfolio_risk(self, portfolio: pd.DataFrame, behavior: InvestmentBehavior) -> Dict:
        """포트폴리오 리스크 평가"""
        return {
            'volatility': behavior.portfolio_volatility,
            'max_drawdown': behavior.max_drawdown,
            'concentration_risk': max(behavior.sector_concentration.values()) if behavior.sector_concentration else 0,
            'liquidity_risk': 1 - behavior.cash_ratio,
            'behavioral_risk': self._calculate_behavioral_risk_score(behavior),
            'overall_risk_score': self._calculate_overall_risk_score(behavior)
        }
    
    def _calculate_behavioral_risk_score(self, behavior: InvestmentBehavior) -> float:
        """행동적 리스크 점수 계산"""
        factors = {
            'turnover_risk': min(behavior.turnover_rate / 100, 1.0) * 0.3,
            'fomo_risk': min(behavior.fomo_purchase_count / 20, 1.0) * 0.2,
            'loss_aversion_risk': behavior.loss_delay_rate * 0.2,
            'concentration_risk': max(behavior.sector_concentration.values()) * 0.3 if behavior.sector_concentration else 0
        }
        return sum(factors.values())
    
    def _calculate_overall_risk_score(self, behavior: InvestmentBehavior) -> float:
        """종합 리스크 점수"""
        return min((
            behavior.portfolio_volatility / 30 * 0.3 +
            behavior.max_drawdown / 50 * 0.3 +
            self._calculate_behavioral_risk_score(behavior) * 0.4
        ), 1.0)
    
    async def _optimize_portfolio(self, current: Dict, risk: Dict, behavior: InvestmentBehavior) -> Dict:
        """포트폴리오 최적화"""
        target_positions = current['positions'].copy()
        
        # 1. 섹터 균형 조정
        for sector, weight in current['sector_weights'].items():
            if weight > self.risk_limits['max_sector_concentration']:
                reduction_factor = self.risk_limits['max_sector_concentration'] / weight
                for stock, data in target_positions.items():
                    if data['sector'] == sector:
                        data['target_weight'] = data['weight'] * reduction_factor
            else:
                for stock, data in target_positions.items():
                    if data['sector'] == sector:
                        data['target_weight'] = data['weight']
        
        # 2. 개별 종목 한도 적용
        for stock, data in target_positions.items():
            if data.get('target_weight', data['weight']) > self.risk_limits['max_single_stock']:
                data['target_weight'] = self.risk_limits['max_single_stock']
        
        # 3. 방어 섹터 추가 (높은 변동성 대응)
        if behavior.portfolio_volatility > Constants.TARGET_KPI['portfolio_volatility']:
            self._add_defensive_sectors(target_positions)
        
        # 4. 현금 비중 확보
        total_weight = sum(data.get('target_weight', data['weight']) for data in target_positions.values())
        if total_weight > (1 - self.risk_limits['min_cash_ratio']):
            adjustment = (1 - self.risk_limits['min_cash_ratio']) / total_weight
            for data in target_positions.values():
                data['target_weight'] = data.get('target_weight', data['weight']) * adjustment
        
        return target_positions
    
    def _add_defensive_sectors(self, positions: Dict):
        """방어적 섹터 추가"""
        current_defensive_weight = sum(
            data.get('target_weight', data['weight']) 
            for data in positions.values() 
            if data['sector'] in self.sector_recommendations['defensive']
        )
        
        if current_defensive_weight < 0.2:  # 20% 미만인 경우
            # 방어 섹터 비중 증가 로직
            pass
    
    def _calculate_required_trades(self, current: Dict, target: Dict) -> List[Dict]:
        """필요한 거래 계산"""
        trades = []
        total_value = sum(pos['value'] for pos in current['positions'].values())
        
        for stock, current_data in current['positions'].items():
            target_data = target.get(stock, {})
            current_weight = current_data['weight']
            target_weight = target_data.get('target_weight', 0)
            
            weight_diff = target_weight - current_weight
            if abs(weight_diff) > 0.01:  # 1% 이상 차이
                trade_value = weight_diff * total_value
                trades.append({
                    'stock_code': stock,
                    'stock_name': current_data.get('stock_name', stock),
                    'sector': current_data['sector'],
                    'action': 'buy' if weight_diff > 0 else 'sell',
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_change': weight_diff,
                    'trade_value': abs(trade_value),
                    'shares': int(abs(trade_value) / current_data['current_price']),
                    'current_price': current_data['current_price'],
                    'priority': self._calculate_trade_priority(current_data, weight_diff)
                })
        
        # 우선순위 정렬
        trades.sort(key=lambda x: x['priority'], reverse=True)
        return trades
    
    def _calculate_trade_priority(self, position_data: Dict, weight_diff: float) -> float:
        """거래 우선순위 계산"""
        priority = abs(weight_diff) * 100
        
        # 손실 포지션 우선 정리
        if position_data.get('pnl_percent', 0) < -10 and weight_diff < 0:
            priority += 20
        
        # 과도한 집중 포지션 우선 조정
        if position_data['weight'] > self.risk_limits['max_single_stock'] and weight_diff < 0:
            priority += 30
        
        return priority
    
    def _create_execution_plan(self, trades: List[Dict], portfolio: pd.DataFrame) -> Dict:
        """실행 계획 생성"""
        sell_trades = [t for t in trades if t['action'] == 'sell']
        buy_trades = [t for t in trades if t['action'] == 'buy']
        
        return {
            'phase1_sells': sell_trades[:5],  # 우선 매도 (최대 5개)
            'phase2_buys': buy_trades[:5],    # 이후 매수 (최대 5개)
            'estimated_days': 3 if len(trades) <= 10 else 5,
            'order_type_recommendation': 'limit_order',  # 지정가 주문 권장
            'execution_tips': [
                "손실 종목부터 정리하여 세금 효과를 고려하세요",
                "거래량이 많은 시간대에 분할 매매하세요",
                "목표가 대비 ±2% 범위에서 체결하세요"
            ]
        }
    
    def _estimate_rebalancing_cost(self, trades: List[Dict]) -> Dict:
        """리밸런싱 비용 추정"""
        total_trade_value = sum(t['trade_value'] for t in trades)
        
        # 미래에셋증권 수수료 (할인 적용)
        commission = total_trade_value * Constants.MSTOCK_DISCOUNT_RATE / 100
        
        # 세금 (매도시)
        sell_value = sum(t['trade_value'] for t in trades if t['action'] == 'sell')
        tax = sell_value * 0.0023  # 거래세 0.23%
        
        # 슬리피지 (예상)
        slippage = total_trade_value * 0.001  # 0.1%
        
        return {
            'commission': commission,
            'tax': tax,
            'slippage': slippage,
            'total_cost': commission + tax + slippage,
            'cost_percentage': (commission + tax + slippage) / total_trade_value * 100
        }

# ===== 게이미피케이션 엔진 =====
class GamificationEngine:
    """게이미피케이션 요소 관리"""
    
    def __init__(self):
        self.badges = {
            'first_week': {'name': '첫 주 완주', 'condition': 'holding_period >= 7', 'points': 100},
            'steady_investor': {'name': '꾸준한 투자자', 'condition': 'consecutive_days >= 30', 'points': 500},
            'risk_manager': {'name': '리스크 관리자', 'condition': 'stop_loss_adherence >= 0.8', 'points': 300},
            'diversifier': {'name': '분산 투자 마스터', 'condition': 'sector_count >= 5', 'points': 400},
            'profit_taker': {'name': '수익 실현 달인', 'condition': 'win_rate >= 0.6', 'points': 600},
            'patience_master': {'name': '인내의 달인', 'condition': 'avg_holding >= 30', 'points': 1000},
            'fomo_fighter': {'name': 'FOMO 극복', 'condition': 'fomo_reduction >= 0.5', 'points': 800}
        }
        self.levels = [
            (0, '투자 입문자'),
            (1000, '투자 수련생'),
            (3000, '투자 중급자'),
            (6000, '투자 고급자'),
            (10000, '투자 전문가'),
            (20000, '투자 마스터')
        ]
        # 실제 구현시 DB 연동
        self.user_data = {}
    
    async def check_achievements(self, behavior: InvestmentBehavior, transactions: pd.DataFrame) -> List[Dict]:
        """달성한 배지 확인"""
        new_badges = []
        user_badges = self.user_data.get(behavior.user_id, {}).get('badges', [])
        
        # 첫 주 완주
        if behavior.avg_holding_period >= 7 and 'first_week' not in user_badges:
            new_badges.append({
                'badge_id': 'first_week',
                'name': self.badges['first_week']['name'],
                'points': self.badges['first_week']['points'],
                'achieved_at': datetime.now().isoformat()
            })
        
        # 수익 실현 달인
        if behavior.win_rate >= 60 and 'profit_taker' not in user_badges:
            new_badges.append({
                'badge_id': 'profit_taker',
                'name': self.badges['profit_taker']['name'],
                'points': self.badges['profit_taker']['points'],
                'achieved_at': datetime.now().isoformat()
            })
        
        # FOMO 극복
        if behavior.fomo_purchase_count <= 5 and 'fomo_fighter' not in user_badges:
            new_badges.append({
                'badge_id': 'fomo_fighter',
                'name': self.badges['fomo_fighter']['name'],
                'points': self.badges['fomo_fighter']['points'],
                'achieved_at': datetime.now().isoformat()
            })
        
        return new_badges
    
    async def calculate_streaks(self, user_id: str, behavior: InvestmentBehavior) -> Dict:
        """연속 달성 기록 계산"""
        return {
            'plan_adherence_streak': 7,  # 계획 준수 연속 일수
            'no_fomo_streak': 14,        # FOMO 없는 연속 일수
            'profit_taking_streak': 3,    # 수익 실현 연속 횟수
            'risk_control_streak': 21     # 리스크 관리 연속 일수
        }
    
    async def calculate_level(self, user_id: str) -> Dict:
        """사용자 레벨 계산"""
        total_points = await self.get_points(user_id)
        
        current_level = None
        next_level = None
        for i, (points, title) in enumerate(self.levels):
            if total_points >= points:
                current_level = {'level': i + 1, 'title': title, 'min_points': points}
            else:
                next_level = {'level': i + 1, 'title': title, 'required_points': points}
                break
        
        return {
            'current': current_level,
            'next': next_level,
            'progress': (total_points - current_level['min_points']) / 
                       (next_level['required_points'] - current_level['min_points']) * 100
                       if next_level else 100
        }
    
    async def get_points(self, user_id: str) -> int:
        """사용자 포인트 조회"""
        # 실제 구현시 DB에서 조회
        return self.user_data.get(user_id, {}).get('points', 0)

# ===== M-STOCK 연동 =====
class MStockIntegration:
    """미래에셋증권 M-STOCK 연동"""
    
    def __init__(self):
        self.api_url = Constants.MSTOCK_API_URL
        self.deep_link_base = "mstock://action"
    
    def generate_deep_link(self, action: CoachingAction) -> str:
        """M-STOCK 딥링크 생성"""
        if action.action_type == 'rebalancing':
            return f"{self.deep_link_base}/rebalancing?action_id={action.action_id}"
        elif action.action_type == 'warning':
            return f"{self.deep_link_base}/set_alert?action_id={action.action_id}"
        elif action.action_type == 'goal_setting':
            return f"{self.deep_link_base}/set_goal?action_id={action.action_id}"
        else:
            return f"{self.deep_link_base}/view?action_id={action.action_id}"
    
    async def execute_rebalancing(self, user_id: str, trades: List[Dict]) -> Dict:
        """리밸런싱 실행 API"""
        # 실제 구현시 M-STOCK API 호출
        execution_results = []
        
        for trade in trades:
            result = {
                'trade_id': str(uuid.uuid4()),
                'stock_code': trade['stock_code'],
                'action': trade['action'],
                'requested_shares': trade['shares'],
                'executed_shares': trade['shares'],  # 시뮬레이션
                'execution_price': trade['current_price'] * (1 + np.random.uniform(-0.01, 0.01)),
                'status': 'completed',
                'executed_at': datetime.now().isoformat()
            }
            execution_results.append(result)
        
        return {
            'execution_id': str(uuid.uuid4()),
            'user_id': user_id,
            'total_trades': len(trades),
            'successful_trades': len(execution_results),
            'failed_trades': 0,
            'commission_saved': sum(t['trade_value'] for t in trades) * 0.04 / 100,
            'execution_results': execution_results
        }
    
    async def set_behavior_alerts(self, user_id: str, alerts: List[Dict]) -> Dict:
        """행동 알림 설정"""
        alert_settings = []
        
        for alert in alerts:
            setting = {
                'alert_id': str(uuid.uuid4()),
                'type': alert['type'],
                'threshold': alert['threshold'],
                'message': alert['message'],
                'enabled': True,
                'created_at': datetime.now().isoformat()
            }
            alert_settings.append(setting)
        
        return {
            'user_id': user_id,
            'alerts_set': len(alert_settings),
            'alert_settings': alert_settings
        }

# ===== A/B 테스트 프레임워크 =====
class ABTestFramework:
    """A/B 테스트 관리"""
    
    def __init__(self):
        self.experiments = {
            'coaching_message_tone': {
                'variants': ['friendly', 'professional', 'motivational'],
                'metrics': ['engagement_rate', 'action_completion_rate']
            },
            'rebalancing_frequency': {
                'variants': ['weekly', 'biweekly', 'monthly'],
                'metrics': ['portfolio_performance', 'user_satisfaction']
            },
            'gamification_intensity': {
                'variants': ['basic', 'moderate', 'intense'],
                'metrics': ['retention_rate', 'behavior_improvement']
            }
        }
    
    def assign_variant(self, user_id: str, experiment_name: str) -> str:
        """사용자를 실험 변형에 할당"""
        # 일관된 할당을 위해 해시 사용
        hash_value = int(hashlib.md5(f"{user_id}_{experiment_name}".encode()).hexdigest(), 16)
        variants = self.experiments[experiment_name]['variants']
        return variants[hash_value % len(variants)]
    
    async def track_event(self, user_id: str, experiment_name: str, event_name: str, value: Any):
        """실험 이벤트 추적"""
        variant = self.assign_variant(user_id, experiment_name)
        
        # 실제 구현시 분석 DB에 저장
        event = {
            'user_id': user_id,
            'experiment': experiment_name,
            'variant': variant,
            'event': event_name,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"A/B test event tracked: {event}")
        return event

# ===== FastAPI 애플리케이션 =====
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any

app = FastAPI(
    title="AI 투자주치의 API",
    description="미래에셋증권 AI Festival - 투자 습관 진단 및 코칭 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스
orchestrator = CoachingOrchestrator()
ab_test = ABTestFramework()

# ===== API 모델 =====
class TransactionData(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    transactions: List[Dict[str, Any]] = Field(..., description="거래 내역 리스트")
    include_market_data: bool = Field(False, description="시장 데이터 포함 여부")

class AnalysisResponse(BaseModel):
    report_id: str
    user_id: str
    analysis_date: str
    behavior_summary: str
    investor_types: List[str]
    coaching_actions: List[Dict]
    improvement_goals: Dict
    gamification: Dict
    mstock_integration: Dict
    expected_improvements: Dict

class RebalancingRequest(BaseModel):
    user_id: str
    execute_immediately: bool = False

class RebalancingResponse(BaseModel):
    plan_id: str
    current_portfolio: Dict
    target_portfolio: Dict
    required_trades: List[Dict]
    execution_plan: Dict
    estimated_cost: Dict
    mstock_executable: bool

# ===== API 엔드포인트 =====
@app.get("/")
async def root():
    """서비스 정보"""
    return {
        "service": "AI 투자주치의",
        "version": "1.0.0",
        "description": "투자 습관을 진단하고, 올바른 행동을 설계하는 AI 코치",
        "powered_by": "미래에셋증권 x HyperCLOVA X"
    }

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_behavior(data: TransactionData, background_tasks: BackgroundTasks):
    """투자 행동 종합 분석"""
    try:
        # DataFrame 변환
        df = pd.DataFrame(data.transactions)
        df['date'] = pd.to_datetime(df['date'])
        
        # 시장 데이터 (옵션)
        market_data = None
        if data.include_market_data:
            # 실제 구현시 시장 데이터 조회
            market_data = pd.DataFrame()
        
        # 종합 리포트 생성
        report = await orchestrator.generate_comprehensive_report(
            data.user_id, df, market_data
        )
        
        # A/B 테스트 이벤트 추적
        background_tasks.add_task(
            ab_test.track_event,
            data.user_id,
            'coaching_message_tone',
            'report_generated',
            1
        )
        
        return AnalysisResponse(**report)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/rebalancing", response_model=RebalancingResponse)
async def get_rebalancing_plan(request: RebalancingRequest):
    """포트폴리오 리밸런싱 계획"""
    try:
        # 사용자 포트폴리오 조회 (실제 구현시 DB)
        portfolio_data = {
            'user_id': request.user_id,
            'positions': [
                {'stock_code': 'A005930', 'stock_name': '삼성전자', 'sector': 'IT', 
                 'shares': 100, 'avg_price': 70000, 'current_price': 72000, 'value': 7200000},
                {'stock_code': 'A035720', 'stock_name': '카카오', 'sector': 'IT',
                 'shares': 50, 'avg_price': 45000, 'current_price': 43000, 'value': 2150000},
                # ... 더 많은 포지션
            ]
        }
        
        portfolio_df = pd.DataFrame(portfolio_data['positions'])
        
        # 행동 분석 (최근 데이터 기반)
        behavior = InvestmentBehavior(
            user_id=request.user_id,
            analysis_date=datetime.now(),
            avg_holding_period=5.9,
            turnover_rate=45.2,
            win_loss_ratio=0.82,
            win_rate=42,
            loss_delay_rate=0.32,
            fomo_purchase_count=12,
            portfolio_volatility=19,
            sector_concentration={'IT': 0.45, '금융': 0.20, '바이오': 0.15},
            total_trades=156,
            avg_trade_size=1000000,
            max_drawdown=23.5,
            cash_ratio=0.08
        )
        
        # 리밸런싱 계획 생성
        plan = await orchestrator.rebalancing_engine.generate_rebalancing_plan(
            portfolio_df, behavior
        )
        
        # 즉시 실행 옵션
        if request.execute_immediately:
            execution_result = await orchestrator.mstock_integration.execute_rebalancing(
                request.user_id, plan['required_trades']
            )
            plan['execution_result'] = execution_result
        
        return RebalancingResponse(**plan)
        
    except Exception as e:
        logger.error(f"Rebalancing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/progress")
async def get_user_progress(user_id: str):
    """사용자 진행 상황 조회"""
    try:
        # 게이미피케이션 정보
        level_info = await orchestrator.gamification_engine.calculate_level(user_id)
        points = await orchestrator.gamification_engine.get_points(user_id)
        
        # 최근 개선 추이 (실제 구현시 DB 조회)
        improvement_trend = {
            'holding_period': [4.2, 5.1, 5.9, 6.5],
            'turnover_rate': [52, 48, 45.2, 42],
            'win_rate': [38, 40, 42, 45],
            'months': ['1월', '2월', '3월', '4월(예상)']
        }
        
        return {
            'user_id': user_id,
            'level': level_info,
            'total_points': points,
            'improvement_trend': improvement_trend,
            'next_milestone': {
                'name': '평균 보유기간 7일 달성',
                'progress': 84.3,
                'reward_points': 500
            }
        }
        
    except Exception as e:
        logger.error(f"Progress query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/alerts/setup")
async def setup_behavior_alerts(user_id: str, alert_configs: List[Dict]):
    """행동 알림 설정"""
    try:
        result = await orchestrator.mstock_integration.set_behavior_alerts(
            user_id, alert_configs
        )
        return result
        
    except Exception as e:
        logger.error(f"Alert setup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/insights")
async def get_market_insights():
    """시장 인사이트 (HyperCLOVA X 활용)"""
    return {
        "daily_brief": "오늘 코스피는 미국 증시 상승에 힘입어 강세를 보일 전망입니다.",
        "sector_outlook": {
            "IT": "긍정적 - AI 관련주 강세 지속",
            "금융": "중립 - 금리 인상 우려와 실적 개선 기대 공존",
            "바이오": "변동성 - 임상 결과 발표 주목"
        },
        "behavioral_tip": "시장이 좋을 때일수록 원칙을 지키는 것이 중요합니다."
    }

@app.get("/api/v1/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "AI Investment Coach",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# ===== 메인 실행 =====
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AI Investment Coach Service...")
    logger.info("미래에셋증권 AI Festival 2025")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
