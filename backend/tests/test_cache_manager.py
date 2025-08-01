"""
캐시 매니저 테스트
"""
import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from backend.cache_manager import CacheManager

class TestCacheManager:
    @pytest.fixture
    async def cache(self):
        """테스트용 임시 캐시 인스턴스"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache = CacheManager(tmp.name)
            await cache.initialize()
            yield cache
            await cache.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_basic_get_set(self, cache):
        """기본 저장/조회 테스트"""
        # 문자열 저장
        await cache.set("test_key", "test_value", ttl=3600)
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # 딕셔너리 저장
        test_dict = {"name": "test", "value": 123}
        await cache.set("dict_key", test_dict, ttl=3600)
        retrieved = await cache.get("dict_key")
        assert retrieved == test_dict
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache):
        """캐시 만료 테스트"""
        # 1초 TTL로 저장
        await cache.set("expire_key", "value", ttl=1)
        
        # 즉시 조회 - 존재해야 함
        value = await cache.get("expire_key")
        assert value == "value"
        
        # 2초 대기 후 조회 - 없어야 함
        await asyncio.sleep(2)
        value = await cache.get("expire_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache):
        """캐시 키 생성 테스트"""
        key1 = cache.generate_cache_key("AAPL", "stock")
        key2 = cache.generate_cache_key("AAPL", "stock")
        
        # 같은 시간대에 생성된 키는 동일해야 함
        assert key1 == key2
        
        # 긴 식별자는 해시 처리
        long_id = "A" * 100
        key3 = cache.generate_cache_key(long_id, "test")
        assert len(key3) < len(long_id) + 20
    
    @pytest.mark.asyncio
    async def test_pattern_matching(self, cache):
        """패턴 매칭 조회 테스트"""
        # 여러 키 저장
        await cache.set("stock_AAPL", {"symbol": "AAPL"}, ttl=3600)
        await cache.set("stock_GOOGL", {"symbol": "GOOGL"}, ttl=3600)
        await cache.set("index_SPY", {"symbol": "SPY"}, ttl=3600)
        
        # 패턴으로 조회
        stocks = await cache.get_pattern("stock_*")
        assert len(stocks) == 2
        assert "stock_AAPL" in stocks
        assert "stock_GOOGL" in stocks
        assert "index_SPY" not in stocks
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """캐시 통계 테스트"""
        # 데이터 저장
        for i in range(5):
            await cache.set(f"key_{i}", f"value_{i}", ttl=3600)
        
        # 일부 키 여러 번 접근
        for _ in range(3):
            await cache.get("key_0")
        
        stats = await cache.get_stats()
        
        assert stats['total_entries'] >= 5
        assert stats['active_entries'] >= 5
        assert len(stats['popular_keys']) > 0
        
        # 가장 많이 접근한 키가 상위에 있어야 함
        if stats['popular_keys']:
            assert stats['popular_keys'][0][0] == "key_0"
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache):
        """동시 접근 테스트"""
        async def write_task(n):
            await cache.set(f"concurrent_{n}", n, ttl=3600)
        
        async def read_task(n):
            return await cache.get(f"concurrent_{n}")
        
        # 동시에 여러 쓰기 작업
        write_tasks = [write_task(i) for i in range(10)]
        await asyncio.gather(*write_tasks)
        
        # 동시에 여러 읽기 작업
        read_tasks = [read_task(i) for i in range(10)]
        results = await asyncio.gather(*read_tasks)
        
        # 모든 값이 올바르게 저장/조회되었는지 확인
        for i, result in enumerate(results):
            assert result == i
    
    @pytest.mark.asyncio
    async def test_error_handling(self, cache):
        """에러 처리 테스트"""
        # 잘못된 JSON 저장 시도
        class NonSerializable:
            pass
        
        # JSON 직렬화 불가능한 객체도 처리되어야 함
        obj = NonSerializable()
        await cache.set("non_serializable", obj, ttl=3600)
        
        # None 값 처리
        await cache.set("none_value", None, ttl=3600)
        value = await cache.get("none_value")
        assert value is None
