#!/usr/bin/env python3
"""
Trading API Client

Async HTTP client for communicating with the trading backend API.
Handles authentication, request formatting, and error handling.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from telegram_integration.config import get_config

logger = logging.getLogger(__name__)


class TradingAPIClient:
    """
    Async client for trading backend API.
    
    Handles all HTTP communication with the FastAPI backend.
    """
    
    def __init__(self):
        """Initialize API client with configuration."""
        self.config = get_config()
        self.base_url = self.config.api_base_url
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Dict with response data
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error("Authentication failed")
                    return {"error": "Authentication failed"}
                else:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    return {"error": f"API error: {response.status}"}
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {"error": "Connection error"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "Unexpected error"}
    
    # Authentication
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with the API.
        
        Args:
            username: User username
            password: User password
            
        Returns:
            Dict with token or error
        """
        result = await self._request(
            "POST",
            "/auth/login",
            data={"username": username, "password": password}
        )
        
        if "access_token" in result:
            self.token = result["access_token"]
            logger.info("Successfully authenticated with API")
        
        return result
    
    # Bot Status & Control
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Dict with bot status information
        """
        return await self._request("GET", "/status")
    
    async def start_trading(self) -> Dict[str, Any]:
        """
        Start the trading bot.
        
        Returns:
            Dict with operation result
        """
        return await self._request("POST", "/bot/start")
    
    async def stop_trading(self) -> Dict[str, Any]:
        """
        Stop the trading bot.
        
        Returns:
            Dict with operation result
        """
        return await self._request("POST", "/bot/stop")
    
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """
        Set trading mode.
        
        Args:
            mode: Trading mode (auto, manual, semi-auto)
            
        Returns:
            Dict with operation result
        """
        return await self._request("POST", "/bot/mode", params={"mode": mode})
    
    # Portfolio & Balance
    
    async def get_balance(self, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account balance.
        
        Args:
            exchange: Optional exchange filter
            
        Returns:
            Dict with balance information
        """
        params = {"exchange": exchange} if exchange else None
        return await self._request("GET", "/portfolio/balances", params=params)
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """
        Get current portfolio positions.
        
        Returns:
            Dict with portfolio data
        """
        return await self._request("GET", "/portfolio/balances")
    
    # Trading Signals
    
    async def get_signals(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent trading signals.
        
        Args:
            limit: Number of signals to retrieve
            
        Returns:
            Dict with signals data
        """
        return await self._request("GET", "/signals/recent", params={"limit": limit})
    
    # Performance & Metrics
    
    async def get_performance(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dict with performance data
        """
        return await self._request("GET", "/performance/metrics")
    
    async def get_trades(self, limit: int = 50) -> Dict[str, Any]:
        """
        Get trade history.
        
        Args:
            limit: Number of trades to retrieve
            
        Returns:
            Dict with trade history
        """
        return await self._request("GET", "/trades/history", params={"limit": limit})
    
    # Additional endpoints (to be implemented)
    
    async def get_exchanges(self) -> Dict[str, Any]:
        """
        Get list of connected exchanges.
        
        Returns:
            Dict with exchange information
        """
        # This would need to be implemented in the backend API
        status = await self.get_status()
        if "connected_exchanges" in status:
            return {"exchanges": status["connected_exchanges"]}
        return {"exchanges": []}
    
    async def analyze_market(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI market analysis.
        
        Args:
            symbol: Optional symbol to analyze
            
        Returns:
            Dict with analysis data
        """
        # Placeholder - would need backend implementation
        params = {"symbol": symbol} if symbol else None
        return await self._request("GET", "/ai/analyze", params=params)
    
    async def get_sentiment(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sentiment analysis.
        
        Args:
            symbol: Optional symbol for sentiment
            
        Returns:
            Dict with sentiment data
        """
        # Placeholder - would need backend implementation
        params = {"symbol": symbol} if symbol else None
        return await self._request("GET", "/ai/sentiment", params=params)


# Global client instance
_client_instance: Optional[TradingAPIClient] = None


def get_client() -> TradingAPIClient:
    """
    Get or create global API client instance.
    
    Returns:
        TradingAPIClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = TradingAPIClient()
    return _client_instance
