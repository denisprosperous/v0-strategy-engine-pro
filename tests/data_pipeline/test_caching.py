"""Unit and Integration Tests for Redis Cache Manager.

Tests caching functionality, TTLs, hit rates, and failover behavior.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from data_pipeline.cache_manager import (
    RedisCacheManager,
    CacheConfig,
    cached,
    get_cache_manager,
    close_cache_manager
)


@pytest.fixture
def cache_config():
    """Create test cache configuration."""
    config = CacheConfig()
    config.REDIS_HOST = 'localhost'
    config.REDIS_PORT = 6379
    config.REDIS_DB = 15  # Use separate DB for tests
    return config


@pytest.fixture
async def cache_manager(cache_config):
    """Create and connect cache manager for tests."""
    manager = RedisCacheManager(config=cache_config)
    
    # Mock Redis client for tests (avoid actual Redis dependency)
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.setex = AsyncMock()
    mock_client.delete = AsyncMock(return_value=0)
    mock_client.keys = AsyncMock(return_value=[])
    mock_client.close = AsyncMock()
    
    manager.client = mock_client
    manager._connected = True
    
    yield manager
    
    await manager.disconnect()


class TestCacheConfig:
    """Test cache configuration."""
    
    def test_market_data_ttl_config(self, cache_config):
        """Test market data TTL configuration."""
        assert cache_config.MARKET_DATA_TTL['1m'] == 5
        assert cache_config.MARKET_DATA_TTL['1h'] == 60
        assert cache_config.MARKET_DATA_TTL['1d'] == 300
    
    def test_order_book_ttl(self, cache_config):
        """Test order book has ultra-fast refresh."""
        assert cache_config.ORDER_BOOK_TTL == 1  # 1 second
    
    def test_account_balance_ttl(self, cache_config):
        """Test account balance TTL."""
        assert cache_config.ACCOUNT_BALANCE_TTL == 60
    
    def test_redis_connection_defaults(self, cache_config):
        """Test Redis connection defaults."""
        assert cache_config.REDIS_HOST == 'localhost'
        assert cache_config.REDIS_PORT == 6379
        assert cache_config.MAX_CONNECTIONS == 50


class TestRedisCacheManager:
    """Test Redis cache manager functionality."""
    
    def test_initialization(self, cache_config):
        """Test manager initialization."""
        manager = RedisCacheManager(config=cache_config)
        assert manager.config == cache_config
        assert manager._connected == False
        assert manager._stats['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_connect_success(self, cache_config):
        """Test successful Redis connection."""
        manager = RedisCacheManager(config=cache_config)
        
        with patch('data_pipeline.cache_manager.ConnectionPool') as mock_pool, \
             patch('data_pipeline.cache_manager.Redis') as mock_redis:
            
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_redis.return_value = mock_client
            
            await manager.connect()
            
            assert manager._connected == True
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, cache_config):
        """Test Redis connection failure gracefully handled."""
        manager = RedisCacheManager(config=cache_config)
        
        with patch('data_pipeline.cache_manager.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
            mock_redis.return_value = mock_client
            
            await manager.connect()
            
            # Should not crash, just disable caching
            assert manager._connected == False
    
    def test_make_key(self, cache_manager):
        """Test cache key generation."""
        key = cache_manager._make_key('market', 'binance', 'BTC/USDT', '1h')
        assert key == 'market:binance:BTC/USDT:1h'
    
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_manager):
        """Test cache GET with hit."""
        test_data = {'price': 50000, 'volume': 100}
        cache_manager.client.get = AsyncMock(
            return_value=json.dumps(test_data)
        )
        
        result = await cache_manager.get('test:key')
        
        assert result == test_data
        assert cache_manager._stats['hits'] == 1
        assert cache_manager._stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_manager):
        """Test cache GET with miss."""
        cache_manager.client.get = AsyncMock(return_value=None)
        
        result = await cache_manager.get('test:key')
        
        assert result is None
        assert cache_manager._stats['hits'] == 0
        assert cache_manager._stats['misses'] == 1
    
    @pytest.mark.asyncio
    async def test_set_cache(self, cache_manager):
        """Test cache SET operation."""
        test_data = {'price': 50000}
        
        result = await cache_manager.set('test:key', test_data, ttl=60)
        
        assert result == True
        assert cache_manager._stats['sets'] == 1
        cache_manager.client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_cache_when_disconnected(self):
        """Test SET fails gracefully when disconnected."""
        manager = RedisCacheManager()
        manager._connected = False
        
        result = await manager.set('test:key', {'data': 'value'}, ttl=60)
        
        assert result == False
        assert manager._stats['sets'] == 0
    
    @pytest.mark.asyncio
    async def test_delete_single_key(self, cache_manager):
        """Test deleting single key."""
        cache_manager.client.delete = AsyncMock(return_value=1)
        
        result = await cache_manager.delete('test:key')
        
        assert result == True
        assert cache_manager._stats['deletes'] == 1
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache_manager):
        """Test deleting keys by pattern."""
        cache_manager.client.keys = AsyncMock(
            return_value=['key:1', 'key:2', 'key:3']
        )
        cache_manager.client.delete = AsyncMock(return_value=3)
        
        deleted = await cache_manager.delete_pattern('key:*')
        
        assert deleted == 3
        assert cache_manager._stats['deletes'] == 3


class TestMarketDataCaching:
    """Test market data specific caching."""
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, cache_manager):
        """Test getting cached market data."""
        test_ohlcv = [
            [1699999999, 50000, 50100, 49900, 50050, 100],
            [1700000000, 50050, 50200, 49950, 50100, 120]
        ]
        cache_manager.client.get = AsyncMock(
            return_value=json.dumps(test_ohlcv)
        )
        
        result = await cache_manager.get_market_data(
            exchange='binance',
            symbol='BTC/USDT',
            interval='1h'
        )
        
        assert result == test_ohlcv
        assert cache_manager._stats['hits'] == 1
    
    @pytest.mark.asyncio
    async def test_set_market_data_with_correct_ttl(self, cache_manager):
        """Test market data cached with interval-specific TTL."""
        test_data = [[1699999999, 50000, 50100, 49900, 50050, 100]]
        
        result = await cache_manager.set_market_data(
            exchange='binance',
            symbol='BTC/USDT',
            interval='1h',
            data=test_data
        )
        
        assert result == True
        
        # Verify correct TTL was used (1h = 60s)
        call_args = cache_manager.client.setex.call_args
        assert call_args[0][1] == 60  # TTL for 1h interval
    
    @pytest.mark.asyncio
    async def test_set_market_data_different_intervals(self, cache_manager):
        """Test different intervals use different TTLs."""
        test_data = [[1699999999, 50000, 50100, 49900, 50050, 100]]
        
        # Test 1m interval (5s TTL)
        await cache_manager.set_market_data(
            'binance', 'BTC/USDT', '1m', test_data
        )
        assert cache_manager.client.setex.call_args[0][1] == 5
        
        # Test 1d interval (300s TTL)
        await cache_manager.set_market_data(
            'binance', 'BTC/USDT', '1d', test_data
        )
        assert cache_manager.client.setex.call_args[0][1] == 300


class TestOrderBookCaching:
    """Test order book caching."""
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, cache_manager):
        """Test getting cached order book."""
        test_book = {
            'bids': [[50000, 1.5], [49990, 2.0]],
            'asks': [[50010, 1.2], [50020, 1.8]]
        }
        cache_manager.client.get = AsyncMock(
            return_value=json.dumps(test_book)
        )
        
        result = await cache_manager.get_order_book(
            exchange='binance',
            symbol='BTC/USDT'
        )
        
        assert result == test_book
    
    @pytest.mark.asyncio
    async def test_set_order_book_ultra_short_ttl(self, cache_manager):
        """Test order book uses ultra-short TTL (1s)."""
        test_book = {
            'bids': [[50000, 1.5]],
            'asks': [[50010, 1.2]]
        }
        
        await cache_manager.set_order_book(
            exchange='binance',
            symbol='BTC/USDT',
            data=test_book
        )
        
        # Verify TTL is 1 second
        call_args = cache_manager.client.setex.call_args
        assert call_args[0][1] == 1


class TestAccountBalanceCaching:
    """Test account balance caching."""
    
    @pytest.mark.asyncio
    async def test_get_account_balance(self, cache_manager):
        """Test getting cached balance."""
        test_balance = {'BTC': 1.5, 'USDT': 10000.0}
        cache_manager.client.get = AsyncMock(
            return_value=json.dumps(test_balance)
        )
        
        result = await cache_manager.get_account_balance(
            exchange='binance',
            account_id='user123'
        )
        
        assert result == test_balance
    
    @pytest.mark.asyncio
    async def test_set_account_balance_ttl(self, cache_manager):
        """Test balance uses 60s TTL."""
        test_balance = {'BTC': 1.5}
        
        await cache_manager.set_account_balance(
            exchange='binance',
            account_id='user123',
            data=test_balance
        )
        
        # Verify TTL is 60 seconds
        call_args = cache_manager.client.setex.call_args
        assert call_args[0][1] == 60


class TestCacheInvalidation:
    """Test cache invalidation strategies."""
    
    @pytest.mark.asyncio
    async def test_invalidate_symbol(self, cache_manager):
        """Test invalidating all data for a symbol."""
        cache_manager.client.keys = AsyncMock(
            return_value=[
                'market:binance:BTC/USDT:1h',
                'market:binance:BTC/USDT:1d',
                'orderbook:binance:BTC/USDT'
            ]
        )
        cache_manager.client.delete = AsyncMock(return_value=3)
        
        deleted = await cache_manager.invalidate_symbol(
            exchange='binance',
            symbol='BTC/USDT'
        )
        
        assert deleted == 3


class TestCacheStatistics:
    """Test cache statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, cache_manager):
        """Test statistics are tracked correctly."""
        # Simulate hits and misses
        cache_manager.client.get = AsyncMock(
            side_effect=[
                json.dumps({'data': 'hit'}),
                None,
                json.dumps({'data': 'hit2'}),
                None
            ]
        )
        
        await cache_manager.get('key1')  # Hit
        await cache_manager.get('key2')  # Miss
        await cache_manager.get('key3')  # Hit
        await cache_manager.get('key4')  # Miss
        
        stats = cache_manager.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['total_requests'] == 4
        assert stats['hit_rate_percent'] == 50.0
    
    def test_reset_stats(self, cache_manager):
        """Test stats reset."""
        cache_manager._stats['hits'] = 100
        cache_manager._stats['misses'] = 50
        
        cache_manager.reset_stats()
        
        assert cache_manager._stats['hits'] == 0
        assert cache_manager._stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_high_hit_rate_target(self, cache_manager):
        """Test achieving 95%+ hit rate target."""
        # Simulate 95 hits, 5 misses
        cache_manager.client.get = AsyncMock(
            side_effect=[
                json.dumps({'data': i}) if i < 95 else None
                for i in range(100)
            ]
        )
        
        for i in range(100):
            await cache_manager.get(f'key{i}')
        
        stats = cache_manager.get_stats()
        assert stats['hit_rate_percent'] >= 95.0


class TestCachedDecorator:
    """Test @cached decorator."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator_hit(self, cache_manager):
        """Test decorator uses cache on hit."""
        call_count = 0
        
        @cached(
            cache_manager,
            key_func=lambda x: f'result:{x}',
            ttl=60
        )
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - cache miss
        cache_manager.client.get = AsyncMock(return_value=None)
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - cache hit
        cache_manager.client.get = AsyncMock(
            return_value=json.dumps(10)
        )
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again


class TestGlobalCacheManager:
    """Test global cache manager singleton."""
    
    @pytest.mark.asyncio
    async def test_get_cache_manager_singleton(self):
        """Test global manager is singleton."""
        with patch('data_pipeline.cache_manager.RedisCacheManager.connect'):
            manager1 = await get_cache_manager()
            manager2 = await get_cache_manager()
            
            assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_close_cache_manager(self):
        """Test closing global manager."""
        with patch('data_pipeline.cache_manager.RedisCacheManager.connect'), \
             patch('data_pipeline.cache_manager.RedisCacheManager.disconnect'):
            
            manager = await get_cache_manager()
            await close_cache_manager()
            
            # Next call should create new instance
            manager2 = await get_cache_manager()
            assert manager is not manager2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
