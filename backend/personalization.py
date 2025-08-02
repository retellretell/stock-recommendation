"""
사용자 개인화 시스템
프로필 기반 맞춤 추천 및 UI 설정
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
import structlog
from dataclasses import dataclass, asdict

logger = structlog.get_logger()

@dataclass
class UserProfile:
    """사용자 프로필 데이터 클래스"""
    user_id: str
    experience_level: str = 'beginner'  # beginner, intermediate, advanced
    risk_tolerance: str = 'moderate'   # conservative, moderate, aggressive
    preferred_sectors: List[str] = None
    investment_style: str = 'balanced'  # growth, value, dividend, balanced
    ui_preferences: Dict = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.preferred_sectors is None:
            self.preferred_sectors = []
        if self.ui_preferences is None:
            self.ui_preferences = {
                'info_density': 'medium',  # low, medium, high
                'chart_type': 'candlestick',  # line, candlestick, area
                'color_scheme': 'default',  # default, colorblind, dark
                'language': 'ko'  # ko, en
            }
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class UserPersonalization:
    """사용자 맞춤화 엔진"""
    
    def __init__(self):
        self.user_profiles = {}  # 실제로는 DB 사용
        self.default_layouts = {
            'beginner': {
                'layout': 'simple',
                'widgets': [
                    'weather_summary',
                    'top_5_stocks',
                    'learning_tips',
                    'simple_portfolio'
                ],
                'show_explanations': True,
                'show_technical': False,
                'max_info_items': 5
            },
            'intermediate': {
                'layout': 'standard',
                'widgets': [
                    'market_overview',
                    'top_10_stocks',
                    'sector_heatmap',
                    'portfolio_tracker',
                    'basic_technical'
                ],
                'show_explanations': True,
                'show_technical': True,
                'max_info_items': 10
            },
            'advanced': {
                'layout': 'advanced',
                'widgets': [
                    'market_heatmap',
                    'sector_rotation',
                    'technical_scanner',
                    'portfolio_analytics',
                    'risk_metrics',
                    'custom_screener'
                ],
                'show_explanations': False,
                'show_technical': True,
                'max_info_items': 20
            }
        }
        
        self.risk_filters = {
            'conservative': {
                'max_volatility': 0.15,
                'min_confidence': 0.7,
                'preferred_sectors': ['금융', '필수소비재', '유틸리티'],
                'avoid_sectors': ['바이오', '게임', '신기술']
            },
            'moderate': {
                'max_volatility': 0.25,
                'min_confidence': 0.5,
                'preferred_sectors': [],  # 모든 섹터
                'avoid_sectors': []
            },
            'aggressive': {
                'max_volatility': 1.0,  # 제한 없음
                'min_confidence': 0.3,
                'preferred_sectors': ['바이오', 'IT', '신기술', '성장주'],
                'avoid_sectors': []
            }
        }
        
    async def create_user_profile(self, user_id: str, preferences: Dict) -> UserProfile:
        """사용자 프로필 생성"""
        try:
            profile = UserProfile(
                user_id=user_id,
                experience_level=preferences.get('experience_level', 'beginner'),
                risk_tolerance=preferences.get('risk_tolerance', 'moderate'),
                preferred_sectors=preferences.get('preferred_sectors', []),
                investment_style=preferences.get('investment_style', 'balanced'),
                ui_preferences=preferences.get('ui_preferences', {})
            )
            
            # 프로필 저장
            self.user_profiles[user_id] = profile
            
            logger.info("user_profile_created", user_id=user_id, profile=asdict(profile))
            
            return profile
            
        except Exception as e:
            logger.error("create_profile_error", user_id=user_id, error=str(e))
            raise
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """사용자 선호도 조회"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return None
        
        return {
            'experience_level': profile.experience_level,
            'risk_tolerance': profile.risk_tolerance,
            'preferred_sectors': profile.preferred_sectors,
            'investment_style': profile.investment_style,
            'ui_preferences': profile.ui_preferences
        }
    
    async def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """사용자 프로필 업데이트"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return False
        
        # 허용된 필드만 업데이트
        allowed_fields = ['experience_level', 'risk_tolerance', 'preferred_sectors', 
                         'investment_style', 'ui_preferences']
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.now()
        
        logger.info("user_profile_updated", user_id=user_id, updates=updates)
        return True
    
    async def get_personalized_dashboard(self, user_id: str) -> Dict:
        """개인화된 대시보드 설정"""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            # 기본 설정 반환
            return self.default_layouts['beginner']
        
        # 경험 수준별 기본 레이아웃
        base_layout = self.default_layouts[profile.experience_level].copy()
        
        # UI 선호도 적용
        if profile.ui_preferences:
            base_layout.update({
                'theme': profile.ui_preferences.get('color_scheme', 'default'),
                'language': profile.ui_preferences.get('language', 'ko'),
                'chart_type': profile.ui_preferences.get('chart_type', 'candlestick'),
                'density': profile.ui_preferences.get('info_density', 'medium')
            })
        
        # 리스크 수준 필터 추가
        base_layout['risk_filters'] = self.risk_filters[profile.risk_tolerance]
        
        # 선호 섹터 추가
        if profile.preferred_sectors:
            base_layout['preferred_sectors'] = profile.preferred_sectors
        
        # 투자 스타일별 추가 위젯
        style_widgets = {
            'growth': ['growth_screener', 'earnings_calendar'],
            'value': ['value_screener', 'fundamental_scanner'],
            'dividend': ['dividend_tracker', 'yield_rankings'],
            'balanced': ['portfolio_optimizer']
        }
        
        if profile.investment_style in style_widgets:
            base_layout['widgets'].extend(style_widgets[profile.investment_style])
        
        return base_layout
    
    async def get_personalized_recommendations(self, user_id: str, stocks: List[Dict]) -> List[Dict]:
        """개인화된 종목 추천"""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            return stocks[:10]  # 기본 상위 10개
        
        # 리스크 필터 적용
        risk_filter = self.risk_filters[profile.risk_tolerance]
        filtered_stocks = []
        
        for stock in stocks:
            # 변동성 체크
            if stock.get('volatility', 0) > risk_filter['max_volatility']:
                continue
            
            # 신뢰도 체크
            if stock.get('confidence', 0) < risk_filter['min_confidence']:
                continue
            
            # 섹터 필터
            stock_sector = stock.get('sector', '')
            
            # 회피 섹터 체크
            if stock_sector in risk_filter['avoid_sectors']:
                continue
            
            # 선호 섹터 가중치
            if stock_sector in profile.preferred_sectors:
                stock['preference_score'] = stock.get('composite_score', 0.5) * 1.2
            else:
                stock['preference_score'] = stock.get('composite_score', 0.5)
            
            filtered_stocks.append(stock)
        
        # 투자 스타일별 추가 필터링
        if profile.investment_style == 'growth':
            # 성장주: EPS 성장률 높은 종목 선호
            filtered_stocks = [s for s in filtered_stocks if s.get('eps_yoy', 0) > 10]
        elif profile.investment_style == 'value':
            # 가치주: PE 비율 낮은 종목 선호
            filtered_stocks = [s for s in filtered_stocks if s.get('pe_ratio', 100) < 20]
        elif profile.investment_style == 'dividend':
            # 배당주: 배당 수익률 높은 종목 선호
            filtered_stocks = [s for s in filtered_stocks if s.get('dividend_yield', 0) > 2]
        
        # preference_score로 정렬
        filtered_stocks.sort(key=lambda x: x.get('preference_score', 0), reverse=True)
        
        # 경험 수준별 추천 개수
        recommendation_count = {
            'beginner': 5,
            'intermediate': 10,
            'advanced': 20
        }
        
        limit = recommendation_count.get(profile.experience_level, 10)
        
        return filtered_stocks[:limit]
    
    async def track_user_behavior(self, user_id: str, action: str, details: Dict):
        """사용자 행동 추적 (학습용)"""
        # 실제로는 이벤트를 DB에 저장
        event = {
            'user_id': user_id,
            'action': action,  # view_stock, add_watchlist, trade, etc.
            'details': details,
            'timestamp': datetime.now()
        }
        
        logger.info("user_behavior_tracked", event=event)
        
        # 행동 패턴 학습 (향후 구현)
        # - 자주 보는 종목의 섹터 → preferred_sectors 자동 업데이트
        # - 거래 패턴 → risk_tolerance 조정
        # - UI 사용 패턴 → ui_preferences 최적화
    
    async def get_learning_content(self, user_id: str) -> List[Dict]:
        """경험 수준별 학습 콘텐츠"""
        profile = self.user_profiles.get(user_id)
        experience_level = profile.experience_level if profile else 'beginner'
        
        content = {
            'beginner': [
                {
                    'id': 'basic_1',
                    'title': '주식 투자의 기초',
                    'topics': [
                        '주식이란 무엇인가?',
                        '주식 시장의 작동 원리',
                        '기본 용어 설명',
                        '투자 vs 투기의 차이'
                    ],
                    'duration': '10분',
                    'difficulty': '초급'
                },
                {
                    'id': 'basic_2',
                    'title': '날씨 예보판 활용법',
                    'topics': [
                        '날씨 아이콘의 의미',
                        '확률과 신뢰도 이해하기',
                        '섹터별 날씨 지도 읽기',
                        '첫 투자 시작하기'
                    ],
                    'duration': '15분',
                    'difficulty': '초급'
                }
            ],
            'intermediate': [
                {
                    'id': 'intermediate_1',
                    'title': '기술적 분석 입문',
                    'topics': [
                        '이동평균선의 이해',
                        'RSI와 MACD 활용',
                        '지지와 저항 개념',
                        '차트 패턴 인식'
                    ],
                    'duration': '20분',
                    'difficulty': '중급'
                },
                {
                    'id': 'intermediate_2',
                    'title': '펀더멘털 분석',
                    'topics': [
                        'ROE, PER의 의미',
                        '재무제표 읽기',
                        '섹터별 특성 이해',
                        '가치 평가 방법'
                    ],
                    'duration': '25분',
                    'difficulty': '중급'
                }
            ],
            'advanced': [
                {
                    'id': 'advanced_1',
                    'title': 'AI 예측 모델의 이해',
                    'topics': [
                        'LSTM과 시계열 예측',
                        'XGBoost의 작동 원리',
                        '앙상블 모델의 장단점',
                        'SHAP을 통한 예측 해석'
                    ],
                    'duration': '30분',
                    'difficulty': '고급'
                },
                {
                    'id': 'advanced_2',
                    'title': '리스크 관리 전략',
                    'topics': [
                        '포트폴리오 이론',
                        'VaR와 CVaR 계산',
                        '헤징 전략',
                        '시스템 트레이딩'
                    ],
                    'duration': '35분',
                    'difficulty': '고급'
                }
            ]
        }
        
        return content.get(experience_level, content['beginner'])
    
    def get_ui_config(self, user_id: str) -> Dict:
        """사용자별 UI 설정"""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            return self._get_default_ui_config()
        
        config = {
            'theme': profile.ui_preferences.get('color_scheme', 'default'),
            'language': profile.ui_preferences.get('language', 'ko'),
            'density': profile.ui_preferences.get('info_density', 'medium'),
            'animations': profile.experience_level != 'beginner',  # 초보자는 애니메이션 최소화
            'tooltips': profile.experience_level == 'beginner',  # 초보자만 툴팁
            'shortcuts': profile.experience_level == 'advanced',  # 고급자만 단축키
            'accessibility': {
                'high_contrast': profile.ui_preferences.get('color_scheme') == 'colorblind',
                'font_size': 'large' if profile.ui_preferences.get('info_density') == 'low' else 'normal',
                'reduce_motion': profile.ui_preferences.get('reduce_motion', False)
            }
        }
        
        return config
    
    def _get_default_ui_config(self) -> Dict:
        """기본 UI 설정"""
        return {
            'theme': 'default',
            'language': 'ko',
            'density': 'medium',
            'animations': True,
            'tooltips': True,
            'shortcuts': False,
            'accessibility': {
                'high_contrast': False,
                'font_size': 'normal',
                'reduce_motion': False
            }
        }
