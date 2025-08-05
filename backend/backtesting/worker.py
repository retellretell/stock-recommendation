"""
백테스팅 워커 프로세스
독립적으로 실행되는 백그라운드 작업 처리
"""
import asyncio
import os
import sys
from pathlib import Path
import structlog

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

from config import settings
from cache_manager import CacheManager
from data_pipeline import DataPipeline
from ml_predictor import StockPredictor
from backtesting.scheduler import BacktestingScheduler

# 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class BacktestingWorker:
    """백테스팅 워커"""
    
    def __init__(self):
        self.scheduler = BacktestingScheduler()
        self.cache = None
        self.data_pipeline = None
        self.predictor = None
        self.running = False
        
    async def initialize(self):
        """워커 초기화"""
        logger.info("backtesting_worker_initializing")
        
        # 캐시 초기화
        self.cache = CacheManager(settings.cache_db_path)
        await self.cache.initialize()
        
        # 데이터 파이프라인 초기화
        self.data_pipeline = DataPipeline(self.cache)
        
        # ML 모델 초기화
        self.predictor = StockPredictor()
        await self.predictor.load_models()
        
        # 스케줄러 초기화
        await self.scheduler.initialize()
        
        # 전역 인스턴스 설정 (스케줄러에서 사용)
        import backend.main as main
        main.data_pipeline = self.data_pipeline
        main.predictor = self.predictor
        
        logger.info("backtesting_worker_initialized")
        
    async def start(self):
        """워커 시작"""
        self.running = True
        logger.info("backtesting_worker_started")
        
        # 작업 태스크들
        tasks = [
            asyncio.create_task(self.scheduler.start()),
            asyncio.create_task(self.health_check_loop()),
            asyncio.create_task(self.periodic_cleanup())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("backtesting_worker_interrupted")
        except Exception as e:
            logger.error("backtesting_worker_error", error=str(e))
        finally:
            await self.stop()
            
    async def stop(self):
        """워커 종료"""
        self.running = False
        await self.scheduler.stop()
        
        if self.cache:
            await self.cache.close()
            
        logger.info("backtesting_worker_stopped")
        
    async def health_check_loop(self):
        """헬스 체크 루프"""
        while self.running:
            try:
                # 메모리 사용량 체크
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                logger.info("worker_health_check",
                           memory_mb=memory_mb,
                           cache_entries=await self._get_cache_size())
                
                # 메모리가 너무 높으면 경고
                if memory_mb > 1024:  # 1GB
                    logger.warning("worker_memory_high", memory_mb=memory_mb)
                    
            except Exception as e:
                logger.error("health_check_error", error=str(e))
                
            await asyncio.sleep(300)  # 5분마다
            
    async def periodic_cleanup(self):
        """주기적 정리 작업"""
        while self.running:
            try:
                # 오래된 예측 정리
                await self.scheduler.tracker.cleanup_old_predictions(days=90)
                
                # 캐시 정리
                if self.cache:
                    stats = await self.cache.get_stats()
                    if stats['total_entries'] > 10000:
                        await self.cache.clear_expired()
                        
                logger.info("periodic_cleanup_completed")
                
            except Exception as e:
                logger.error("cleanup_error", error=str(e))
                
            await asyncio.sleep(86400)  # 24시간마다
            
    async def _get_cache_size(self) -> int:
        """캐시 크기 조회"""
        if self.cache:
            stats = await self.cache.get_stats()
            return stats.get('total_entries', 0)
        return 0

# 메인 함수
async def main():
    """메인 함수"""
    worker = BacktestingWorker()
    
    try:
        await worker.initialize()
        await worker.start()
    except Exception as e:
        logger.error("worker_main_error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    # 환경 변수 설정
    os.environ['WORKER_TYPE'] = 'backtesting'
    
    # 프로세스 이름 설정
    try:
        import setproctitle
        setproctitle.setproctitle('stock-backtesting-worker')
    except ImportError:
        pass
        
    # 실행
    asyncio.run(main())
