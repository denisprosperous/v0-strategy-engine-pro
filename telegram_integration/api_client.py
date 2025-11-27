#!/usr/bin/env python3
"""
API Client for Telegram Bot

Handles all HTTP communication with the FastAPI backend.
Includes robust error handling and authentication.

Author: v0-strategy-engine-pro
Version: 1.0.0
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class APIClient:
    """
    Singleton API client for communicating with backend.
    
    Manages authentication, session handling, and error recovery.
    """
    
    _instance = None
    _session = None
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(APIClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize API client."""
        if self._initialized:
            return
        
        self.base_url = os.getenv("API_URL", "http://localhost:8000")
        self.token = None
        self._initialized = True
        logger.info(f"API Client initialized with base URL: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication.
        
        Returns:
            Dict with headers including auth token if available
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
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
        Make HTTP request to API with comprehensive error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Dict with response data or detailed error information
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.request(
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
                    logger.error("Authentication failed - invalid or expired token")
                    return {
                        "error": "Authentication failed. Please check your login credentials.",
                        "details": "Your session may have expired. Try logging in again.",
                        "error_code": "AUTH_FAILED"
                    }
                
                elif response.status == 404:
                    logger.error(f"Endpoint not found: {url}")
                    return {
                        "error": "API endpoint not found",
                        "details": f"The requested endpoint '{endpoint}' does not exist. This feature may not be implemented yet.",
                        "error_code": "NOT_FOUND"
                    }
                
                elif response.status == 500:
                    error_text = await response.text()
                    logger.error(f"Server error: {error_text}")
                    return {
                        "error": "Backend server error",
                        "details": "The trading engine encountered an internal error. Please try again later or contact support.",
                        "error_code": "SERVER_ERROR"
                    }
                
                else:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    return {
                        "error": f"API request failed (Status: {response.status})",
                        "details": error_text[:200] if error_text else "Unknown error",
                        "error_code": f"HTTP_{response.status}"
                    }
        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error - cannot reach backend: {e}")
            return {
                "error": "Cannot connect to trading backend",
                "details": f"Backend API at {self.base_url} is not reachable. "
                          f"Please check:\n"
                          f"1. Backend server is running\n"
                          f"2. API_URL environment variable is correct (currently: {self.base_url})\n"
                          f"3. Network connectivity",
                "error_code": "CONNECTION_ERROR"
            }
        
        except aiohttp.ClientTimeout as e:
            logger.error(f"Request timeout: {e}")
            return {
                "error": "Request timeout",
                "details": "The backend took too long to respond (>30s). The server may be overloaded.",
                "error_code": "TIMEOUT"
            }
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {
                "error": "Network error",
                "details": f"A network error occurred: {str(e)[:200]}",
                "error_code": "CLIENT_ERROR"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "error": "Unexpected error",
                "details": f"An unexpected error occurred: {str(e)[:200]}. Check logs for details.",
                "error_code": "UNKNOWN_ERROR"
            }
    
    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with backend and store token.
        
        Args:
            username: User login username
            password: User login password
            
        Returns:
            Dict with authentication result
        """
        result = await self._request(
            "POST",
            "/api/auth/login",
            data={"username": username, "password": password}
        )
        
        if "access_token" in result:
            self.token = result["access_token"]
            logger.info(f"Successfully authenticated as {username}")
            return {"success": True, "message": "Authentication successful"}
        else:
            logger.error(f"Authentication failed for {username}")
            return result
    
    async def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        return await self._request("GET", "/api/status")
    
    async def get_portfolio_balances(self) -> Dict[str, Any]:
        """Get portfolio balances."""
        return await self._request("GET", "/api/portfolio/balances")
    
    async def get_recent_signals(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent trading signals."""
        return await self._request("GET", "/api/signals/recent", params={"limit": limit})
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return await self._request("GET", "/api/performance/metrics")
    
    async def get_trade_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get trade history."""
        return await self._request("GET", "/api/trades/history", params={"limit": limit})
    
    async def start_bot(self) -> Dict[str, Any]:
        """Start the trading bot."""
        return await self._request("POST", "/api/bot/start")
    
    async def stop_bot(self) -> Dict[str, Any]:
        """Stop the trading bot."""
        return await self._request("POST", "/api/bot/stop")
    
    async def set_bot_mode(self, mode: str) -> Dict[str, Any]:
        """
        Set bot trading mode.
        
        Args:
            mode: Trading mode ('auto', 'manual', 'semi-auto')
            
        Returns:
            Dict with result
        """
        return await self._request("POST", "/api/bot/mode", params={"mode": mode})
    
    async def get_ai_analysis(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI market analysis.
        
        Args:
            symbol: Optional symbol to analyze
            
        Returns:
            Dict with AI analysis
        """
        params = {"symbol": symbol} if symbol else {}
        return await self._request("GET", "/api/ai/analyze", params=params)
    
    async def get_sentiment(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sentiment analysis.
        
        Args:
            symbol: Optional symbol for sentiment
            
        Returns:
            Dict with sentiment data
        """
        params = {"symbol": symbol} if symbol else {}
        return await self._request("GET", "/api/ai/sentiment", params=params)
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("API client session closed")
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.token is not None


# Global singleton instance
api_client = APIClient()
