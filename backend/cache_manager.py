"""
SQLite 기반 캐시 매니저 (개선된 버전)
"""
import aiosqlite
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
import hashlib
from contextlib import asynccontextmanager

from exceptions import CacheError

logger = structlog.get_logger()

class CacheManager:
    """비동기 SQLite 캐시 관리자"""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self.conn = None
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """캐시 DB 초기화"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            
            # WAL 모드 활성화 (동시성 향상)
            await self.conn.execute("PRAGMA journal_mode=WAL")
            
            # 캐시 테이블 생성
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
            """)
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pattern ON cache(key)
            """)
            
            await self.conn.commit()
            
            # 만료된 항목 정리 태스크 시작
            asyncio.create_task(self._cleanup_expired())
            
            self._initialized = True
            logger.info("cache_initialized", db_path=self.db_path)
            
        except Exception as e:
            logger.error("cache_initialization_failed", error=str(e))
            raise CacheError(f"캐시 초기화 실패: {e}")
    
    def generate_cache_key(self, identifier: str, data_type: str) -> str:
        """캐시 키 생성 with 버전 관리"""
        date_str = datetime.now().strftime("%Y%m%d")
        hour_bucket = datetime.now().hour // 3  # 3시간 단위
        
        # 키가 너무 길어지는 것을 방지하기 위한 해시
        if len(identifier) > 50:
            identifier_hash = hashlib.md5(identifier.encode()).hexdigest()[:10]
            return f"v1:{data_type}:{identifier_hash}:{date_str}:{hour_bucket}"
        
        return f"v1:{data_type}:{identifier}:{date_str}:{hour_bucket}"
    
    @asynccontextmanager
    async def _get_connection(self):
        """데이터베이스 연결 컨텍스트 관리자"""
        if not self._initialized:
            raise CacheError("캐시가 초기화되지 않았습니다")
        
        async with self._lock:
            yield self.conn
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        try:
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT value, expires_at FROM cache 
                    WHERE key = ? AND expires_at > ?
                    """,
                    (key, datetime.now().isoformat())
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # 접근 횟수 업데이트
                await conn.execute(
                    """
                    UPDATE cache 
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE key = ?
                    """,
                    (datetime.now().isoformat(), key)
                )
                await conn.commit()
                
                # JSON 파싱
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
                    
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """캐시에 값 저장"""
        try:
            async with self._get_connection() as conn:
                expires_at = datetime.now() + timedelta(seconds=ttl)
                value_str = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
                
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, value_str, expires_at.isoformat(), datetime.now().isoformat())
                )
                await conn.commit()
                
                logger.debug("cache_set", key=key, ttl=ttl)
                
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            raise CacheError(f"캐시 저장 실패: {e}")
    
    async def delete(self, key: str):
        """캐시에서 값 삭제"""
        try:
            async with self._get_connection() as conn:
                await conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                await conn.commit()
                
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """패턴 매칭으로 여러 값 조회"""
        try:
            async with self._get_connection() as conn:
                # SQLite LIKE 패턴으로 변환
                like_pattern = pattern.replace('*', '%')
                
                cursor = await conn.execute(
                    """
                    SELECT key, value FROM cache 
                    WHERE key LIKE ? AND expires_at > ?
                    ORDER BY last_accessed DESC
                    LIMIT 1000
                    """,
                    (like_pattern, datetime.now().isoformat())
                )
                
                results = {}
                async for row in cursor:
                    try:
                        results[row['key']] = json.loads(row['value'])
                    except json.JSONDecodeError:
                        results[row['key']] = row['value']
                
                return results
                
        except Exception as e:
            logger.error("cache_get_pattern_error", pattern=pattern, error=str(e))
            return {}
    
    async def health_check(self) -> bool:
        """캐시 상태 확인"""
        try:
            async with self._get_connection() as conn:
                cursor = await conn.execute("SELECT COUNT(*) as count FROM cache")
                row = await cursor.fetchone()
                
                logger.info("cache_health_check", total_entries=row['count'])
                return True
                
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            async with self._get_connection() as conn:
                # 전체 항목 수
                cursor = await conn.execute("SELECT COUNT(*) as total FROM cache")
                total = (await cursor.fetchone())['total']
                
                # 만료된 항목 수
                cursor = await conn.execute(
                    "SELECT COUNT(*) as expired FROM cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                expired = (await cursor.fetchone())['expired']
                
                # 자주 사용되는 키 (상위 10개)
                cursor = await conn.execute("""
                    SELECT key, access_count 
                    FROM cache 
                    ORDER BY access_count DESC 
                    LIMIT 10
                """)
                popular_keys = [(row['key'], row['access_count']) async for row in cursor]
                
                return {
                    'total_entries': total,
                    'expired_entries': expired,
                    'active_entries': total - expired,
                    'popular_keys': popular_keys
                }
                
        except Exception as e:
            logger.error("cache_stats_error", error=str(e))
            return {}
    
    async def _cleanup_expired(self):
        """만료된 캐시 항목 정리 (백그라운드)"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 실행
                
                async with self._get_connection() as conn:
                    # 만료된 항목 삭제
                    cursor = await conn.execute(
                        "DELETE FROM cache WHERE expires_at < ?",
                        (datetime.now().isoformat(),)
                    )
                    deleted_count = cursor.rowcount
                    
                    # 오래된 접근 기록 정리 (30일 이상)
                    old_date = (datetime.now() - timedelta(days=30)).isoformat()
                    await conn.execute(
                        "DELETE FROM cache WHERE last_accessed < ? AND expires_at < ?",
                        (old_date, datetime.now().isoformat())
                    )
                    
                    await conn.commit()
                    
                    if deleted_count > 0:
                        logger.info("cache_cleanup", deleted_count=deleted_count)
                        
            except Exception as e:
                logger.error("cache_cleanup_error", error=str(e))
                await asyncio.sleep(60)  # 에러 발생 시 1분 후 재시도
    
    async def clear_all(self):
        """모든 캐시 삭제 (주의: 개발/테스트용)"""
        try:
            async with self._get_connection() as conn:
                await conn.execute("DELETE FROM cache")
                await conn.commit()
                logger.warning("cache_cleared_all")
                
        except Exception as e:
            logger.error("cache_clear_all_error", error=str(e))
            raise CacheError(f"캐시 전체 삭제 실패: {e}")
    
    async def close(self):
        """연결 종료"""
        if self.conn:
            await self.conn.close()
            self._initialized = False
            logger.info("cache_closed")
