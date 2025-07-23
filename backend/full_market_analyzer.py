"""
전체 한국 주식 시장 분석 시스템
KOSPI, KOSDAQ 전 종목 + 섹터별 분석
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class KoreaStockUniverse:
    """한국 전체 주식 종목 관리"""
    
    def __init__(self):
        self.kospi_stocks = {}
        self.kosdaq_stocks = {}
        self.sector_mapping = {}
        self.etf_list = {}
        
    async def load_all_stocks(self):
        """전체 종목 리스트 로드"""
        try:
            # 방법 1: KRX 공식 데이터 (가장 정확)
            await self._load_from_krx()
            
            # 방법 2: 네이버 금융 크롤링 (백업)
            if not self.kospi_stocks:
                await self._load_from_naver()
                
            # 방법 3: 하드코딩된 주요 종목 (최후의 수단)
            if not self.kospi_stocks:
                self._load_hardcoded_stocks()
                
            logger.info(f"종목 로드 완료: KOSPI {len(self.kospi_stocks)}개, KOSDAQ {len(self.kosdaq_stocks)}개")
            
        except Exception as e:
            logger.error(f"종목 로드 실패: {e}")
            self._load_hardcoded_stocks()
    
    async def _load_from_krx(self):
        """KRX에서 전체 종목 정보 가져오기"""
        try:
            # KRX API 엔드포인트
            url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
            
            # KOSPI 종목
            kospi_data = {
                'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
                'locale': 'ko_KR',
                'mktId': 'STK',
                'trdDd': datetime.now().strftime('%Y%m%d')
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=kospi_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get('output', []):
                            self.kospi_stocks[item['ISU_SRT_CD']] = {
                                'name': item['ISU_NM'],
                                'code': item['ISU_SRT_CD'],
                                'market': 'KOSPI',
                                'sector': item.get('IDX_NM', '기타')
                            }
                
                # KOSDAQ 종목
                kosdaq_data = kospi_data.copy()
                kosdaq_data['mktId'] = 'KSQ'
                
                async with session.post(url, data=kosdaq_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get('output', []):
                            self.kosdaq_stocks[item['ISU_SRT_CD']] = {
                                'name': item['ISU_NM'],
                                'code': item['ISU_SRT_CD'],
                                'market': 'KOSDAQ',
                                'sector': item.get('IDX_NM', '기타')
                            }
                            
        except Exception as e:
            logger.error(f"KRX 데이터 로드 실패: {e}")
    
    async def _load_from_naver(self):
        """네이버 금융에서 종목 정보 크롤링"""
        try:
            # KOSPI
            kospi_url = "https://finance.naver.com/sise/sise_market_sum.nhn?sosok=0"
            kosdaq_url = "https://finance.naver.com/sise/sise_market_sum.nhn?sosok=1"
            
            async with aiohttp.ClientSession() as session:
                # 페이지 수 확인
                async with session.get(kospi_url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    last_page = int(soup.find_all('td', class_='pgRR')[0].find('a')['href'].split('=')[-1])
                
                # 모든 페이지 크롤링
                for page in range(1, min(last_page + 1, 50)):  # 최대 50페이지
                    url = f"{kospi_url}&page={page}"
                    async with session.get(url) as response:
                        html = await response.text()
                        self._parse_naver_stocks(html, 'KOSPI')
                        
        except Exception as e:
            logger.error(f"네이버 크롤링 실패: {e}")
    
    def _parse_naver_stocks(self, html: str, market: str):
        """네이버 금융 HTML 파싱"""
        soup = BeautifulSoup(html, 'html.parser')
        stock_list = soup.find_all('tr', {'onmouseover': True})
        
        for stock in stock_list:
            try:
                name_tag = stock.find('a', class_='tltle')
                if name_tag:
                    name = name_tag.text
                    code = name_tag['href'].split('=')[-1]
                    
                    stock_data = {
                        'name': name,
                        'code': code,
                        'market': market,
                        'sector': '미분류'
                    }
                    
                    if market == 'KOSPI':
                        self.kospi_stocks[code] = stock_data
                    else:
                        self.kosdaq_stocks[code] = stock_data
                        
            except Exception:
                continue
    
    def _load_hardcoded_stocks(self):
        """하드코딩된 주요 종목 (최소한의 데이터)"""
        # 시가총액 상위 종목들
        major_stocks = {
            # KOSPI 대형주
            "005930": ("삼성전자", "전기전자", "KOSPI"),
            "000660": ("SK하이닉스", "전기전자", "KOSPI"),
            "005490": ("POSCO홀딩스", "철강금속", "KOSPI"),
            "005380": ("현대차", "운수장비", "KOSPI"),
            "051910": ("LG화학", "화학", "KOSPI"),
            "006400": ("삼성SDI", "전기전자", "KOSPI"),
            "035420": ("NAVER", "서비스업", "KOSPI"),
            "003550": ("LG", "서비스업", "KOSPI"),
            "017670": ("SK텔레콤", "통신업", "KOSPI"),
            "105560": ("KB금융", "금융", "KOSPI"),
            "055550": ("신한지주", "금융", "KOSPI"),
            "032830": ("삼성생명", "보험", "KOSPI"),
            "003490": ("대한항공", "운수창고", "KOSPI"),
            "010130": ("고려아연", "비철금속", "KOSPI"),
            "009150": ("삼성전기", "전기전자", "KOSPI"),
            "018260": ("삼성에스디에스", "서비스업", "KOSPI"),
            "033780": ("KT&G", "음식료품", "KOSPI"),
            "015760": ("한국전력", "전기가스업", "KOSPI"),
            "034730": ("SK", "서비스업", "KOSPI"),
            "012330": ("현대모비스", "운수장비", "KOSPI"),
            
            # KOSDAQ 대형주
            "247540": ("에코프로비엠", "화학", "KOSDAQ"),
            "086520": ("에코프로", "서비스업", "KOSDAQ"),
            "373220": ("LG에너지솔루션", "전기전자", "KOSPI"),
            "207940": ("삼성바이오로직스", "의약품", "KOSPI"),
            "068270": ("셀트리온", "의약품", "KOSPI"),
            "035720": ("카카오", "서비스업", "KOSPI"),
            "035900": ("JYP Ent.", "오락문화", "KOSDAQ"),
            "041510": ("에스엠", "오락문화", "KOSDAQ"),
            "352820": ("하이브", "오락문화", "KOSDAQ"),
            "036570": ("엔씨소프트", "서비스업", "KOSPI"),
            "251270": ("넷마블", "서비스업", "KOSPI"),
            "263750": ("펄어비스", "서비스업", "KOSDAQ"),
            "293490": ("카카오게임즈", "서비스업", "KOSDAQ"),
            "112040": ("위메이드", "서비스업", "KOSDAQ"),
        }
        
        # 섹터별 분류
        self.sector_mapping = {
            "전기전자": ["005930", "000660", "006400", "009150", "373220"],
            "화학": ["051910", "247540"],
            "자동차": ["005380", "012330"],
            "금융": ["105560", "055550", "032830"],
            "바이오": ["207940", "068270"],
            "IT서비스": ["035420", "035720", "018260"],
            "게임": ["036570", "251270", "263750", "293490", "112040"],
            "엔터": ["035900", "041510", "352820"],
            "철강금속": ["005490", "010130"],
            "운송": ["003490"],
            "통신": ["017670"],
            "유틸리티": ["015760"],
            "음식료": ["033780"]
        }
        
        for code, (name, sector, market) in major_stocks.items():
            stock_data = {
                'name': name,
                'code': code,
                'market': market,
                'sector': sector
            }
            
            if market == 'KOSPI':
                self.kospi_stocks[code] = stock_data
            else:
                self.kosdaq_stocks[code] = stock_data
    
    def get_all_stocks(self) -> Dict[str, Dict]:
        """전체 종목 반환"""
        all_stocks = {}
        all_stocks.update(self.kospi_stocks)
        all_stocks.update(self.kosdaq_stocks)
        return all_stocks
    
    def get_stocks_by_sector(self, sector: str) -> List[Dict]:
        """섹터별 종목 반환"""
        stocks = []
        for code, data in self.get_all_stocks().items():
            if data['sector'] == sector:
                stocks.append(data)
        return stocks
    
    def get_sector_list(self) -> List[str]:
        """전체 섹터 리스트"""
        sectors = set()
        for stock in self.get_all_stocks().values():
            sectors.add(stock['sector'])
        return sorted(list(sectors))


class MarketWideAnalyzer:
    """전체 시장 분석기"""
    
    def __init__(self):
        self.stock_universe = KoreaStockUniverse()
        self.news_analyzer = EnhancedNewsAnalyzer()
        self.sector_scores = {}
        self.market_indicators = {}
        
    async def analyze_entire_market(self) -> Dict:
        """전체 시장 분석"""
        # 1. 전체 종목 로드
        await self.stock_universe.load_all_stocks()
        all_stocks = self.stock_universe.get_all_stocks()
        
        logger.info(f"전체 {len(all_stocks)}개 종목 분석 시작")
        
        # 2. 뉴스 수집 및 분석
        news_results = await self._collect_market_news()
        
        # 3. 섹터별 분석
        sector_analysis = await self._analyze_by_sector(news_results)
        
        # 4. 개별 종목 점수 계산
        stock_scores = await self._calculate_stock_scores(all_stocks, news_results)
        
        # 5. 시장 전체 지표 계산
        market_summary = self._calculate_market_indicators(stock_scores, sector_analysis)
        
        # 6. 추천 종목 선정
        recommendations = self._select_recommendations(stock_scores, top_n=20)
        avoid_list = self._select_avoid_list(stock_scores, top_n=10)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(all_stocks),
            'market_summary': market_summary,
            'sector_analysis': sector_analysis,
            'top_recommendations': recommendations,
            'stocks_to_avoid': avoid_list,
            'detailed_scores': stock_scores
        }
    
    async def _collect_market_news(self) -> Dict:
        """전체 시장 뉴스 수집"""
        news_sources = [
            "https://finance.naver.com/news/",
            "https://www.hankyung.com/finance",
            "https://www.mk.co.kr/economy/stock",
            "https://www.sedaily.com/Stock",
            "https://biz.chosun.com/stock"
        ]
        
        all_news = []
        
        # 비동기로 여러 소스에서 뉴스 수집
        async with aiohttp.ClientSession() as session:
            tasks = []
            for source in news_sources:
                tasks.append(self._fetch_news_from_source(session, source))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_news.extend(result)
        
        # 뉴스 분석
        analyzed_news = self._analyze_news_batch(all_news)
        
        return analyzed_news
    
    async def _fetch_news_from_source(self, session: aiohttp.ClientSession, url: str) -> List[Dict]:
        """특정 소스에서 뉴스 가져오기"""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_news_html(html, url)
        except Exception as e:
            logger.error(f"뉴스 수집 실패 {url}: {e}")
            return []
    
    def _parse_news_html(self, html: str, source_url: str) -> List[Dict]:
        """HTML에서 뉴스 추출"""
        soup = BeautifulSoup(html, 'html.parser')
        news_list = []
        
        # 소스별 파싱 로직 (간략화)
        if "naver" in source_url:
            news_items = soup.find_all('dl', class_='articleList')
            for item in news_items[:20]:  # 최근 20개
                try:
                    title = item.find('a').text.strip()
                    news_list.append({
                        'title': title,
                        'source': 'naver',
                        'timestamp': datetime.now()
                    })
                except:
                    continue
        
        return news_list
    
    def _analyze_news_batch(self, news_list: List[Dict]) -> Dict:
        """뉴스 배치 분석"""
        stock_mentions = defaultdict(list)
        sector_sentiments = defaultdict(list)
        
        for news in news_list:
            # 종목 언급 추출
            mentioned_stocks = self._extract_stock_mentions(news['title'])
            
            # 감성 분석
            sentiment, confidence = self.news_analyzer.analyze_sentiment(news['title'])
            
            for stock_code, stock_name in mentioned_stocks:
                stock_mentions[stock_code].append({
                    'sentiment': sentiment,
                    'confidence': confidence,
                    'title': news['title']
                })
                
                # 섹터별 감성 집계
                stock_info = self.stock_universe.get_all_stocks().get(stock_code)
                if stock_info:
                    sector = stock_info['sector']
                    sector_sentiments[sector].append(sentiment)
        
        return {
            'stock_mentions': dict(stock_mentions),
            'sector_sentiments': dict(sector_sentiments)
        }
    
    def _extract_stock_mentions(self, text: str) -> List[Tuple[str, str]]:
        """텍스트에서 종목 언급 추출"""
        mentioned = []
        
        for code, stock_info in self.stock_universe.get_all_stocks().items():
            if stock_info['name'] in text:
                mentioned.append((code, stock_info['name']))
        
        return mentioned
    
    async def _analyze_by_sector(self, news_results: Dict) -> Dict:
        """섹터별 분석"""
        sector_analysis = {}
        
        for sector in self.stock_universe.get_sector_list():
            sentiments = news_results.get('sector_sentiments', {}).get(sector, [])
            
            if sentiments:
                positive_count = sentiments.count('positive')
                negative_count = sentiments.count('negative')
                total_count = len(sentiments)
                
                score = (positive_count - negative_count) / total_count if total_count > 0 else 0
                
                sector_analysis[sector] = {
                    'score': score,
                    'sentiment_distribution': {
                        'positive': positive_count,
                        'negative': negative_count,
                        'neutral': sentiments.count('neutral')
                    },
                    'total_mentions': total_count,
                    'trend': 'bullish' if score > 0.2 else 'bearish' if score < -0.2 else 'neutral'
                }
            else:
                sector_analysis[sector] = {
                    'score': 0,
                    'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                    'total_mentions': 0,
                    'trend': 'neutral'
                }
        
        return sector_analysis
    
    async def _calculate_stock_scores(self, all_stocks: Dict, news_results: Dict) -> Dict:
        """개별 종목 점수 계산"""
        stock_scores = {}
        stock_mentions = news_results.get('stock_mentions', {})
        
        for code, stock_info in all_stocks.items():
            # 뉴스 점수
            news_score = 0
            mentions = stock_mentions.get(code, [])
            
            if mentions:
                positive = sum(1 for m in mentions if m['sentiment'] == 'positive')
                negative = sum(1 for m in mentions if m['sentiment'] == 'negative')
                total = len(mentions)
                
                news_score = (positive - negative) / total if total > 0 else 0
                mention_count = total
            else:
                mention_count = 0
            
            # 섹터 점수 (해당 섹터의 전반적인 분위기)
            sector = stock_info['sector']
            sector_score = self.sector_scores.get(sector, {}).get('score', 0)
            
            # 종합 점수 (뉴스 70% + 섹터 30%)
            final_score = (news_score * 0.7) + (sector_score * 0.3)
            
            # 언급 횟수에 따른 신뢰도
            confidence = min(1.0, mention_count / 10)  # 10회 이상 언급시 신뢰도 100%
            
            stock_scores[code] = {
                'name': stock_info['name'],
                'sector': sector,
                'market': stock_info['market'],
                'news_score': news_score,
                'sector_score': sector_score,
                'final_score': final_score,
                'confidence': confidence,
                'mention_count': mention_count
            }
        
        return stock_scores
    
    def _calculate_market_indicators(self, stock_scores: Dict, sector_analysis: Dict) -> Dict:
        """시장 전체 지표 계산"""
        # 전체 종목 점수 분포
        all_scores = [s['final_score'] for s in stock_scores.values()]
        
        # 긍정/부정 종목 수
        positive_stocks = sum(1 for s in all_scores if s > 0.1)
        negative_stocks = sum(1 for s in all_scores if s < -0.1)
        neutral_stocks = len(all_scores) - positive_stocks - negative_stocks
        
        # 시장 심리 지수 (0-100)
        market_sentiment = (positive_stocks / len(all_scores)) * 100 if all_scores else 50
        
        # 가장 강한/약한 섹터
        sorted_sectors = sorted(sector_analysis.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return {
            'market_sentiment_index': market_sentiment,
            'total_stocks': len(all_scores),
            'positive_stocks': positive_stocks,
            'negative_stocks': negative_stocks,
            'neutral_stocks': neutral_stocks,
            'strongest_sectors': [s[0] for s in sorted_sectors[:3]],
            'weakest_sectors': [s[0] for s in sorted_sectors[-3:]],
            'market_trend': 'bullish' if market_sentiment > 60 else 'bearish' if market_sentiment < 40 else 'neutral'
        }
    
    def _select_recommendations(self, stock_scores: Dict, top_n: int = 20) -> List[Dict]:
        """추천 종목 선정"""
        # 신뢰도가 높고 점수가 높은 종목 선정
        filtered_stocks = [
            (code, data) for code, data in stock_scores.items()
            if data['confidence'] > 0.3 and data['final_score'] > 0.2
        ]
        
        # 점수순 정렬
        sorted_stocks = sorted(filtered_stocks, key=lambda x: x[1]['final_score'], reverse=True)
        
        recommendations = []
        for code, data in sorted_stocks[:top_n]:
            recommendations.append({
                'code': code,
                'name': data['name'],
                'sector': data['sector'],
                'market': data['market'],
                'score': data['final_score'],
                'confidence': data['confidence'],
                'reasons': self._generate_recommendation_reasons(data)
            })
        
        return recommendations
    
    def _select_avoid_list(self, stock_scores: Dict, top_n: int = 10) -> List[Dict]:
        """회피 종목 선정"""
        # 신뢰도가 높고 점수가 낮은 종목
        filtered_stocks = [
            (code, data) for code, data in stock_scores.items()
            if data['confidence'] > 0.3 and data['final_score'] < -0.2
        ]
        
        sorted_stocks = sorted(filtered_stocks, key=lambda x: x[1]['final_score'])
        
        avoid_list = []
        for code, data in sorted_stocks[:top_n]:
            avoid_list.append({
                'code': code,
                'name': data['name'],
                'sector': data['sector'],
                'market': data['market'],
                'score': data['final_score'],
                'confidence': data['confidence'],
                'reasons': self._generate_avoid_reasons(data)
            })
        
        return avoid_list
    
    def _generate_recommendation_reasons(self, stock_data: Dict) -> List[str]:
        """추천 이유 생성"""
        reasons = []
        
        if stock_data['news_score'] > 0.3:
            reasons.append("긍정적인 뉴스가 다수 보도됨")
        
        if stock_data['sector_score'] > 0.2:
            reasons.append(f"{stock_data['sector']} 섹터 전반적으로 강세")
        
        if stock_data['mention_count'] > 5:
            reasons.append("시장의 높은 관심도")
        
        if stock_data['market'] == 'KOSPI' and stock_data['final_score'] > 0.5:
            reasons.append("대형주 안정성과 성장성 겸비")
        
        return reasons
    
    def _generate_avoid_reasons(self, stock_data: Dict) -> List[str]:
        """회피 이유 생성"""
        reasons = []
        
        if stock_data['news_score'] < -0.3:
            reasons.append("부정적인 뉴스 다수")
        
        if stock_data['sector_score'] < -0.2:
            reasons.append(f"{stock_data['sector']} 섹터 전반적으로 약세")
        
        if stock_data['mention_count'] > 5 and stock_data['news_score'] < 0:
            reasons.append("부정적인 시장 관심 집중")
        
        return reasons


class EnhancedNewsAnalyzer:
    """향상된 뉴스 분석기"""
    
    def __init__(self):
        self.positive_keywords = {
            'strong': ['신고가', '급등', '상한가', '대박', '흑자전환', '어닝서프라이즈', '수주', '계약'],
            'medium': ['상승', '상승세', '호조', '개선', '증가', '성장', '회복', '반등'],
            'weak': ['보합', '소폭상승', '긍정적', '기대', '관심']
        }
        
        self.negative_keywords = {
            'strong': ['하한가', '급락', '폭락', '적자전환', '리콜', '소송', '파산', '상장폐지'],
            'medium': ['하락', '하락세', '부진', '감소', '악화', '우려', '불안'],
            'weak': ['보합', '소폭하락', '조정', '차익실현']
        }
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """텍스트 감성 분석"""
        text_lower = text.lower()
        
        positive_score = 0
        negative_score = 0
        
        # 긍정 키워드 점수
        for strength, keywords in self.positive_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if strength == 'strong':
                        positive_score += 3
                    elif strength == 'medium':
                        positive_score += 2
                    else:
                        positive_score += 1
        
        # 부정 키워드 점수
        for strength, keywords in self.negative_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if strength == 'strong':
                        negative_score += 3
                    elif strength == 'medium':
                        negative_score += 2
                    else:
                        negative_score += 1
        
        # 최종 감성 결정
        total_score = positive_score - negative_score
        
        if total_score > 2:
            sentiment = 'positive'
            confidence = min(0.9, 0.5 + total_score * 0.1)
        elif total_score < -2:
            sentiment = 'negative'
            confidence = min(0.9, 0.5 + abs(total_score) * 0.1)
        else:
            sentiment = 'neutral'
            confidence = 0.5
        
        return sentiment, confidence
