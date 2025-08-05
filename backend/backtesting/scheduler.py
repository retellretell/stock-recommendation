"""
백테스팅 일일 체크 스케줄러
"""
import asyncio
import schedule
import time
from datetime import datetime, timedelta
import structlog

from .tracker import PredictionTracker
from .paper_trading import PaperTradingEngine
from .analyzer import PerformanceAnalyzer
from ..main import data_pipeline, predictor
from ..cache_manager import CacheManager

logger = structlog.get_logger()

class BacktestingScheduler:
    """백테스팅 작업 스케줄러"""
    
    def __init__(self, db_path: str = "backtesting.db"):
        self.db_path = db_path
        self.tracker = PredictionTracker(db_path)
        self.paper_trading = PaperTradingEngine(db_path)
        self.analyzer = PerformanceAnalyzer(db_path)
        self.cache = CacheManager()
        self.running = False
        
    async def initialize(self):
        """초기화"""
        await self.tracker.initialize()
        await self.paper_trading.initialize()
        await self.cache.initialize()
        
        logger.info("backtesting_scheduler_initialized")
        
    async def start(self):
        """스케줄러 시작"""
        self.running = True
        
        # 스케줄 설정
        schedule.every().day.at("09:00").do(lambda: asyncio.create_task(self.morning_routine()))
        schedule.every().day.at("16:00").do(lambda: asyncio.create_task(self.afternoon_check()))
        schedule.every().day.at("22:00").do(lambda: asyncio.create_task(self.daily_report()))
        schedule.every().week.do(lambda: asyncio.create_task(self.weekly_report()))
        
        logger.info("scheduler_started")
        
        # 스케줄 실행 루프
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # 1분마다 체크
            
    async def stop(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("scheduler_stopped")
        
    async def morning_routine(self):
        """아침 루틴 (09:00)"""
        try:
            logger.info("morning_routine_started")
            
            # 1. 새로운 예측 생성 및 저장
            await self.generate_daily_predictions()
            
            # 2. 어제 예측 결과 확인
            await self.tracker.check_predictions(days_after=1)
            
            # 3. 포트폴리오 리밸런싱
            await self.rebalance_portfolio()
            
            logger.info("morning_routine_completed")
            
        except Exception as e:
            logger.error("morning_routine_error", error=str(e))
            
    async def afternoon_check(self):
        """오후 체크 (16:00)"""
        try:
            logger.info("afternoon_check_started")
            
            # 1. 당일 예측 결과 확인
            await self.check_intraday_performance()
            
            # 2. 포트폴리오 가치 업데이트
            await self.update_portfolio_values()
            
            # 3. 리스크 체크
            await self.check_risk_limits()
            
            logger.info("afternoon_check_completed")
            
        except Exception as e:
            logger.error("afternoon_check_error", error=str(e))
            
    async def daily_report(self):
        """일일 리포트 생성 (22:00)"""
        try:
            logger.info("daily_report_started")
            
            # 1. 3일, 7일 전 예측 결과 확인
            await self.tracker.check_predictions(days_after=3)
            await self.tracker.check_predictions(days_after=7)
            
            # 2. 일일 성과 분석
            start_date = datetime.now().replace(hour=0, minute=0, second=0)
            end_date = datetime.now()
            
            daily_metrics = await self.tracker.calculate_performance_metrics('daily')
            
            # 3. 알림 생성
            await self.generate_notifications(daily_metrics)
            
            logger.info("daily_report_completed", 
                       accuracy=daily_metrics.accuracy_rate,
                       predictions=daily_metrics.total_predictions)
            
        except Exception as e:
            logger.error("daily_report_error", error=str(e))
            
    async def weekly_report(self):
        """주간 리포트 생성"""
        try:
            logger.info("weekly_report_started")
            
            # 1. 주간 성과 분석
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            report = await self.analyzer.generate_report(start_date, end_date)
            
            # 2. 리포트 저장
            await self.save_report(report, 'weekly')
            
            # 3. 오래된 데이터 정리
            await self.tracker.cleanup_old_predictions()
            
            logger.info("weekly_report_completed")
            
        except Exception as e:
            logger.error("weekly_report_error", error=str(e))
            
    async def generate_daily_predictions(self):
        """일일 예측 생성"""
        # 관심 종목 리스트
        watchlist = await self.get_watchlist()
        
        for ticker in watchlist:
            try:
                # 최신 데이터 가져오기
                stock_data = await data_pipeline.get_stock_data(ticker)
                
                if stock_data:
                    # 예측 생성
                    prediction = await predictor.predict_single(stock_data)
                    
                    # 예측 저장
                    prediction_id = await self.tracker.save_prediction(
                        ticker, 
                        prediction,
                        stock_data['current_price']
                    )
                    
                    # Paper Trading 처리
                    await self.paper_trading.process_prediction(
                        ticker,
                        {**prediction, 'id': prediction_id},
                        stock_data['current_price']
                    )
                    
            except Exception as e:
                logger.error("prediction_generation_error", 
                           ticker=ticker, 
                           error=str(e))
                           
    async def get_watchlist(self) -> List[str]:
        """관심 종목 리스트 가져오기"""
        # 캐시에서 인기 종목 가져오기
        cache_stats = await self.cache.get_stats()
        popular_tickers = [key.split('_')[1] for key, _ in cache_stats.get('popular_keys', [])]
        
        # 기본 종목 추가
        default_tickers = [
            '005930', '000660', '035420', '051910', '006400',  # KR
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'          # US
        ]
        
        # 중복 제거
        return list(set(popular_tickers + default_tickers))[:50]  # 최대 50개
        
    async def rebalance_portfolio(self):
        """포트폴리오 리밸런싱"""
        config = self.paper_trading.config
        
        # 리밸런싱 주기 체크
        if config.rebalance_frequency == 'daily':
            pass  # 매일 실행
        elif config.rebalance_frequency == 'weekly' and datetime.now().weekday() != 0:
            return  # 월요일만 실행
        elif config.rebalance_frequency == 'monthly' and datetime.now().day != 1:
            return  # 매월 1일만 실행
            
        # 현재 포지션 확인
        portfolio = await self.paper_trading.get_portfolio_summary()
        
        for position in portfolio['positions']:
            ticker = position['ticker']
            pnl_pct = position['pnl_pct']
            
            # 손절/익절 체크
            if pnl_pct < -config.stop_loss * 100:
                await self.paper_trading.close_position(ticker, "stop_loss")
                logger.info("position_closed_stop_loss", ticker=ticker, loss=pnl_pct)
                
            elif pnl_pct > config.take_profit * 100:
                await self.paper_trading.close_position(ticker, "take_profit")
                logger.info("position_closed_take_profit", ticker=ticker, profit=pnl_pct)
                
    async def update_portfolio_values(self):
        """포트폴리오 현재가 업데이트"""
        portfolio = await self.paper_trading.get_portfolio_summary()
        current_prices = {}
        
        # 각 포지션의 현재가 조회
        for position in portfolio['positions']:
            ticker = position['ticker']
            stock_data = await data_pipeline.get_stock_data(ticker)
            
            if stock_data:
                current_prices[ticker] = stock_data['current_price']
                
        # 포트폴리오 업데이트
        await self.paper_trading.update_portfolio_values(current_prices)
        
    async def check_intraday_performance(self):
        """당일 성과 확인"""
        # 오늘 생성된 예측들 조회
        today = datetime.now().replace(hour=0, minute=0, second=0)
        predictions = await self.tracker.get_recent_predictions(limit=100)
        
        today_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p['prediction_date']) >= today
        ]
        
        if today_predictions:
            logger.info("intraday_performance",
                       total_predictions=len(today_predictions),
                       avg_confidence=sum(p['confidence'] for p in today_predictions) / len(today_predictions))
                       
    async def check_risk_limits(self):
        """리스크 한도 체크"""
        portfolio = self.paper_trading.portfolio
        
        # 최대 낙폭 체크
        if abs(portfolio.max_drawdown) > 25:
            logger.warning("risk_limit_exceeded",
                         metric="max_drawdown",
                         value=portfolio.max_drawdown)
                         
            # 모든 포지션 청산
            for ticker in list(portfolio.positions.keys()):
                await self.paper_trading.close_position(ticker, "risk_limit")
                
        # 포지션 집중도 체크
        if portfolio.positions:
            position_values = [
                pos['quantity'] * pos.get('current_price', pos['avg_price'])
                for pos in portfolio.positions.values()
            ]
            
            max_position = max(position_values)
            concentration = max_position / portfolio.total_value
            
            if concentration > 0.3:  # 30% 이상
                logger.warning("position_concentration_high",
                             concentration=concentration)
                             
    async def generate_notifications(self, metrics: PerformanceMetrics):
        """알림 생성"""
        notifications = []
        
        # 정확도 알림
        if metrics.accuracy_rate < 0.45:
            notifications.append({
                'type': 'alert',
                'message': f"예측 정확도가 {metrics.accuracy_rate:.1%}로 낮습니다."
            })
        elif metrics.accuracy_rate > 0.65:
            notifications.append({
                'type': 'success',
                'message': f"예측 정확도가 {metrics.accuracy_rate:.1%}로 우수합니다!"
            })
            
        # 수익률 알림
        if metrics.paper_trading_return_pct > 5:
            notifications.append({
                'type': 'success',
                'message': f"오늘 수익률이 {metrics.paper_trading_return_pct:.1f}%입니다!"
            })
        elif metrics.paper_trading_return_pct < -3:
            notifications.append({
                'type': 'warning',
                'message': f"오늘 손실이 {abs(metrics.paper_trading_return_pct):.1f}% 발생했습니다."
            })
            
        # 알림 저장/전송 (실제 구현 시)
        for notif in notifications:
            logger.info("notification", **notif)
            
    async def save_report(self, report: Dict, report_type: str):
        """리포트 저장"""
        # 실제로는 DB나 파일로 저장
        logger.info("report_saved", 
                   report_type=report_type,
                   period=report['period'])
                   
# 독립 실행 시
if __name__ == "__main__":
    async def main():
        scheduler = BacktestingScheduler()
        await scheduler.initialize()
        
        try:
            await scheduler.start()
        except KeyboardInterrupt:
            await scheduler.stop()
            
    asyncio.run(main())
