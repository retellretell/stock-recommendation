"""
대체 데이터 수집 및 분석
소셜 미디어, 뉴스, 검색 트렌드 등
"""
import aiohttp
import asyncio
import feedparser
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import re
from textblob import TextBlob
import structlog

logger = structlog.get_logger()

class AlternativeDataAnalyzer:
    """소셜 미디어 및 대체 데이터 분석"""
    
    def __init__(self):
        self.session = None
        self.sentiment_keywords = {
            'positive': {
                'strong': ['급등', '신고가', '상한가', '대박', '흑자전환', '어닝서프라이즈', 
                          '수주', '계약', '상장', 'IPO', '합병', '인수'],
                'medium': ['상승', '상승세', '호조', '개선', '증가', '성장', '회복', '반등',
                          '호재', '긍정적', '기대', '전망'],
                'weak': ['보합', '소폭상승', '관심', '주목']
            },
            'negative': {
                'strong': ['급락', '하한가', '폭락', '적자전환', '리콜', '소송', '파산',
                          '상장폐지', '횡령', '배임', '스캔들'],
                'medium': ['하락', '하락세', '부진', '감소', '악화', '우려', '불안',
                          '악재', '부정적', '실망', '경고'],
                'weak': ['보합', '소폭하락', '조정', '차익실현']
            }
        }
        
        # Reddit 관련 설정
        self.reddit_headers = {
            'User-Agent': 'StockWeatherBot/1.0'
        }
        
    async def _ensure_session(self):
        """세션 확인 및 생성"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def analyze_social_sentiment(self, ticker: str) -> Dict:
        """종합 소셜 감성 분석"""
        try:
            await self._ensure_session()
            
            # 병렬로 여러 소스 분석
            tasks = [
                self._analyze_reddit(ticker),
                self._get_google_trends(ticker),
                self._analyze_news_rss(ticker),
                self._analyze_naver_news(ticker) if ticker.endswith('.KS') or ticker.endswith('.KQ') else asyncio.create_task(self._dummy_task())
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 집계
            reddit_sentiment = results[0] if not isinstance(results[0], Exception) else 0
            search_trend = results[1] if not isinstance(results[1], Exception) else 50
            news_sentiment = results[2] if not isinstance(results[2], Exception) else 0
            naver_sentiment = results[3] if not isinstance(results[3], Exception) else 0
            
            # 가중 평균 계산
            weights = {
                'reddit': 0.2,
                'trends': 0.2,
                'news': 0.4,
                'naver': 0.2
            }
            
            composite_score = (
                reddit_sentiment * weights['reddit'] +
                (search_trend / 100) * weights['trends'] +
                news_sentiment * weights['news'] +
                naver_sentiment * weights['naver']
            )
            
            return {
                'reddit_sentiment': reddit_sentiment,
                'search_interest': search_trend,
                'news_sentiment': news_sentiment,
                'naver_sentiment': naver_sentiment,
                'composite_score': max(0, min(1, composite_score)),  # 0-1 범위로 정규화
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("social_sentiment_analysis_error", ticker=ticker, error=str(e))
            return {
                'reddit_sentiment': 0.5,
                'search_interest': 50,
                'news_sentiment': 0.5,
                'composite_score': 0.5
            }
    
    async def _analyze_reddit(self, ticker: str) -> float:
        """Reddit 감성 분석"""
        try:
            subreddits = ['stocks', 'investing', 'StockMarket', 'wallstreetbets']
            all_sentiments = []
            
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    'q': ticker,
                    'limit': 25,
                    'sort': 'new',
                    't': 'week'  # 최근 1주일
                }
                
                async with self.session.get(url, headers=self.reddit_headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        for post in posts:
                            post_data = post.get('data', {})
                            title = post_data.get('title', '')
                            selftext = post_data.get('selftext', '')
                            
                            # 제목과 본문 감성 분석
                            title_sentiment = self._analyze_text_sentiment(title)
                            text_sentiment = self._analyze_text_sentiment(selftext) if selftext else title_sentiment
                            
                            # 투표 수 가중치
                            score = post_data.get('score', 0)
                            weight = min(1 + np.log1p(abs(score)) / 10, 2)  # 최대 2배 가중치
                            
                            combined_sentiment = (title_sentiment + text_sentiment) / 2
                            all_sentiments.append(combined_sentiment * weight)
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            if all_sentiments:
                # 가중 평균
                return np.average(all_sentiments) / 2 + 0.5  # -1~1을 0~1로 변환
            
            return 0.5  # 중립
            
        except Exception as e:
            logger.error("reddit_analysis_error", ticker=ticker, error=str(e))
            return 0.5
    
    async def _get_google_trends(self, ticker: str) -> float:
        """Google 트렌드 관심도 (0-100)"""
        try:
            # Google Trends는 공식 API가 없으므로 pytrends 라이브러리 사용
            # 여기서는 더미 구현 (실제로는 pytrends 사용)
            
            # 임시: 랜덤 값 반환
            import random
            base_interest = random.uniform(30, 70)
            
            # 최근 뉴스가 많으면 관심도 증가
            news_boost = await self._get_news_volume(ticker) * 20
            
            return min(100, base_interest + news_boost)
            
        except Exception as e:
            logger.error("google_trends_error", ticker=ticker, error=str(e))
            return 50
    
    async def _analyze_news_rss(self, ticker: str) -> float:
        """RSS 뉴스 피드 감성 분석"""
        try:
            # Google News RSS
            rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            
            feed = await asyncio.get_event_loop().run_in_executor(
                None, feedparser.parse, rss_url
            )
            
            if not feed.entries:
                return 0.5
            
            sentiments = []
            for entry in feed.entries[:20]:  # 최근 20개
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                
                # 감성 분석
                title_sentiment = self._analyze_text_sentiment(title)
                summary_sentiment = self._analyze_text_sentiment(summary)
                
                # 시간 가중치 (최신 뉴스일수록 높은 가중치)
                published = entry.get('published_parsed')
                if published:
                    age_days = (datetime.now() - datetime(*published[:6])).days
                    time_weight = max(0.5, 1 - age_days / 7)  # 1주일 이내 뉴스 가중치
                else:
                    time_weight = 0.5
                
                combined = (title_sentiment * 0.7 + summary_sentiment * 0.3) * time_weight
                sentiments.append(combined)
            
            if sentiments:
                return np.mean(sentiments) / 2 + 0.5  # -1~1을 0~1로 변환
            
            return 0.5
            
        except Exception as e:
            logger.error("news_rss_analysis_error", ticker=ticker, error=str(e))
            return 0.5
    
    async def _analyze_naver_news(self, ticker: str) -> float:
        """네이버 뉴스 감성 분석 (한국 주식)"""
        try:
            # 종목명으로 검색 (실제로는 종목코드→종목명 매핑 필요)
            search_query = ticker.replace('.KS', '').replace('.KQ', '')
            
            url = f"https://search.naver.com/search.naver"
            params = {
                'where': 'news',
                'query': f"{search_query} 주가",
                'sort': '0',  # 최신순
                'photo': '0',
                'field': '0',
                'pd': '4',  # 1주일
                'ds': '',
                'de': '',
                'docid': '',
                'related': '0',
                'mynews': '0',
                'office_type': '0',
                'office_section_code': '0',
                'news_office_checked': '',
                'nso': 'so:r,p:1w,a:all',
                'is_sug_officeid': '0'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # BeautifulSoup으로 파싱
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_items = soup.find_all('div', class_='news_area')
                    
                    sentiments = []
                    for item in news_items[:10]:  # 상위 10개
                        title_elem = item.find('a', class_='news_tit')
                        desc_elem = item.find('div', class_='news_dsc')
                        
                        if title_elem:
                            title = title_elem.text
                            desc = desc_elem.text if desc_elem else ''
                            
                            # 한국어 감성 분석
                            sentiment = self._analyze_korean_sentiment(title + ' ' + desc)
                            sentiments.append(sentiment)
                    
                    if sentiments:
                        return np.mean(sentiments)
            
            return 0.5
            
        except Exception as e:
            logger.error("naver_news_analysis_error", ticker=ticker, error=str(e))
            return 0.5
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """영문 텍스트 감성 분석 (-1 ~ 1)"""
        try:
            # TextBlob 사용
            blob = TextBlob(text)
            
            # 감성 점수 (-1 ~ 1)
            polarity = blob.sentiment.polarity
            
            # 주식 관련 키워드 보정
            text_lower = text.lower()
            
            # 긍정 키워드
            if any(word in text_lower for word in ['buy', 'bullish', 'upgrade', 'beat', 'surge']):
                polarity += 0.2
            
            # 부정 키워드
            if any(word in text_lower for word in ['sell', 'bearish', 'downgrade', 'miss', 'crash']):
                polarity -= 0.2
            
            return max(-1, min(1, polarity))
            
        except Exception as e:
            logger.error("text_sentiment_error", error=str(e))
            return 0
    
    def _analyze_korean_sentiment(self, text: str) -> float:
        """한국어 감성 분석 (0 ~ 1)"""
        positive_score = 0
        negative_score = 0
        
        # 키워드 기반 분석
        for strength, keywords in self.sentiment_keywords['positive'].items():
            for keyword in keywords:
                count = text.count(keyword)
                if count > 0:
                    weight = {'strong': 3, 'medium': 2, 'weak': 1}[strength]
                    positive_score += count * weight
        
        for strength, keywords in self.sentiment_keywords['negative'].items():
            for keyword in keywords:
                count = text.count(keyword)
                if count > 0:
                    weight = {'strong': 3, 'medium': 2, 'weak': 1}[strength]
                    negative_score += count * weight
        
        # 정규화
        total_score = positive_score + negative_score
        if total_score == 0:
            return 0.5
        
        sentiment = positive_score / total_score
        return sentiment
    
    async def _get_news_volume(self, ticker: str) -> float:
        """뉴스 볼륨 (0-1)"""
        try:
            # 간단한 구현: RSS 피드의 최근 뉴스 개수
            rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            
            feed = await asyncio.get_event_loop().run_in_executor(
                None, feedparser.parse, rss_url
            )
            
            # 최근 24시간 뉴스 개수
            recent_count = 0
            for entry in feed.entries:
                published = entry.get('published_parsed')
                if published:
                    age_hours = (datetime.now() - datetime(*published[:6])).total_seconds() / 3600
                    if age_hours < 24:
                        recent_count += 1
            
            # 정규화 (10개 이상이면 최대)
            return min(1.0, recent_count / 10)
            
        except Exception as e:
            logger.error("news_volume_error", ticker=ticker, error=str(e))
            return 0
    
    async def get_sector_sentiment(self, sector: str) -> float:
        """섹터별 감성 분석"""
        try:
            # 섹터 관련 키워드
            sector_keywords = {
                'IT': ['tech', 'technology', 'software', 'AI', 'semiconductor'],
                '전자': ['전자', '반도체', 'IT', '소프트웨어'],
                '바이오': ['bio', 'pharma', 'healthcare', 'drug'],
                '제약': ['제약', '바이오', '신약', '임상'],
                '금융': ['finance', 'bank', 'insurance'],
                '자동차': ['auto', 'vehicle', 'EV', 'car'],
                '화학': ['chemical', 'material'],
                '철강': ['steel', 'metal'],
                '건설': ['construction', 'infrastructure'],
                '유통': ['retail', 'commerce'],
                '게임': ['game', 'gaming', 'entertainment'],
                '엔터': ['entertainment', 'media', 'content']
            }
            
            keywords = sector_keywords.get(sector, [sector])
            
            # 여러 키워드로 뉴스 검색 및 분석
            sentiments = []
            for keyword in keywords:
                sentiment = await self._analyze_news_rss(keyword)
                sentiments.append(sentiment)
            
            if sentiments:
                return np.mean(sentiments)
            
            return 0.5
            
        except Exception as e:
            logger.error("sector_sentiment_error", sector=sector, error=str(e))
            return 0.5
    
    async def _dummy_task(self):
        """더미 태스크 (None 반환)"""
        return 0
    
    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
