"""
SQLite 기반 캐시 매니저
"""
import aiosqlite
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

class CacheManager:
    """비동기 SQLite 캐시 관리자"""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self.conn = None
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """캐시 DB 초기화"""
        self.conn = await aiosqlite.connect(self.db_path)
        
        # 캐시 테이블 생성
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 인덱스 생성
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        """)
        
        await self.conn.commit()
        
        # 만료된 항목 정리
        asyncio.create_task(self._cleanup_expired())
        
        logger.info("캐시 매니저 초기화 완료")
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        async with self._lock:
            cursor = await self.conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            value_str, expires_at = row
            expires_dt = datetime.fromisoformat(expires_at)
            
            # 만료 확인
            if datetime.now() > expires_dt:
                await self.delete(key)
                return None
            
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
      """캐시에 값 저장"""
        async with self._lock:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            await self.conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expires_at)
                VALUES (?, ?, ?)
                """,
                (key, value_str, expires_at.isoformat())
            )
            await self.conn.commit()
    
    async def delete(self, key: str):
        """캐시에서 값 삭제"""
        async with self._lock:
            await self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            await self.conn.commit()
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """패턴 매칭으로 여러 값 조회"""
        async with self._lock:
            # SQLite LIKE 패턴으로 변환
            like_pattern = pattern.replace('*', '%')
            
            cursor = await self.conn.execute(
                """
                SELECT key, value FROM cache 
                WHERE key LIKE ? AND expires_at > ?
                """,
                (like_pattern, datetime.now().isoformat())
            )
            
            results = {}
            async for row in cursor:
                key, value_str = row
                try:
                    results[key] = json.loads(value_str)
                except json.JSONDecodeError:
                    results[key] = value_str
            
            return results
    
    async def health_check(self) -> bool:
        """캐시 상태 확인"""
        try:
            await self.conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"캐시 헬스체크 실패: {e}")
            return False
    
    async def _cleanup_expired(self):
        """만료된 캐시 항목 정리 (백그라운드)"""
        while True:
            try:
                async with self._lock:
                    deleted = await self.conn.execute(
                        "DELETE FROM cache WHERE expires_at < ?",
                        (datetime.now().isoformat(),)
                    )
                    await self.conn.commit()
                    
                    if deleted.rowcount > 0:
                        logger.info(f"만료된 캐시 {deleted.rowcount}개 삭제")
                
                # 1시간마다 정리
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"캐시 정리 오류: {e}")
                await asyncio.sleep(60)
    
    async def close(self):
        """연결 종료"""
        if self.conn:
            await self.conn.close()
