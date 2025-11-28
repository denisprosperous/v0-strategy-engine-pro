#!/usr/bin/env python3
"""
FastAPI Backend for Trading Dashboard - Enhanced with Real Data

Provides REST API endpoints for:
- Authentication
- Portfolio data (from exchanges)
- Trading signals
- Performance metrics
- Real-time updates

Author: v0-strategy-engine-pro
Version: 2.0
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import jwt
import os
import sys
import httpx
import hmac
import hashlib
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize FastAPI
app = FastAPI(
    title="Strategy Engine Pro API",
    description="AI-Enhanced Trading Bot Dashboard API",
    version="2.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# Exchange API configurations
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BITGET_API_KEY = os.getenv("BITGET_API_KEY", "")
BITGET_API_SECRET = os.getenv("BITGET_API_SECRET", "")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
    
    def _sign(self, params: dict) -> str:
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def get_account_balance(self) -> List[dict]:
        if not self.api_key:
            return []
        
        async with httpx.AsyncClient() as client:
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            params["signature"] = self._sign(params)
            
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/account",
                    params=params,
                    headers={"X-MBX-APIKEY": self.api_key},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    balances = []
                    for b in data.get("balances", []):
                        free = float(b["free"])
                        locked = float(b["locked"])
                        if free > 0 or locked > 0:
                            balances.append({
                                "asset": b["asset"],
                                "free": free,
                                "locked": locked,
                                "total": free + locked
                            })
                    return balances
            except Exception as e:
                print(f"Binance API error: {e}")
            
            return []
    
    async def get_ticker_price(self, symbol: str) -> float:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/ticker/price",
                    params={"symbol": symbol},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return float(response.json()["price"])
            except:
                pass
        return 0.0

# Initialize clients
binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Bot state
bot_state = {
    "is_running": False,
    "mode": "manual",
    "ai_enabled": False,
    "last_update": datetime.utcnow()
}

# ========== DATA MODELS ==========

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PortfolioBalance(BaseModel):
    asset: str
    free: float
    locked: float
    total: float
    usd_value: float

class TradeSignal(BaseModel):
    id: str
    symbol: str
    direction: str
    tier: int
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    timestamp: datetime
    status: str

class PerformanceMetrics(BaseModel):
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    sharpe_ratio: float
    max_drawdown: float

class BotStatus(BaseModel):
    is_running: bool
    mode: str
    ai_enabled: bool
    connected_exchanges: List[str]
    active_signals: int
    open_positions: int
    last_update: datetime

# ========== AUTHENTICATION ==========

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ========== API ENDPOINTS ==========

@app.get("/")
async def root():
    return {
        "name": "Strategy Engine Pro API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "features": ["real_exchange_data", "live_trading", "ai_signals"]
    }

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    # TODO: Implement proper user authentication with database
    if request.username == "admin" and request.password == "changeme":
        access_token = create_access_token(data={"sub": request.username})
        return TokenResponse(access_token=access_token)
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/status", response_model=BotStatus)
async def get_bot_status(username: str = Depends(verify_token)):
    connected_exchanges = []
    if BINANCE_API_KEY:
        connected_exchanges.append("Binance")
    if BITGET_API_KEY:
        connected_exchanges.append("Bitget")
    
    return BotStatus(
        is_running=bot_state["is_running"],
        mode=bot_state["mode"],
        ai_enabled=bot_state["ai_enabled"],
        connected_exchanges=connected_exchanges,
        active_signals=0,
        open_positions=0,
        last_update=bot_state["last_update"]
    )

@app.get("/api/portfolio/balances", response_model=List[PortfolioBalance])
async def get_portfolio_balances(username: str = Depends(verify_token)):
    balances = []
    
    # Get Binance balances
    binance_balances = await binance_client.get_account_balance()
    for b in binance_balances:
        # Get USD value
        usd_value = b["total"]
        if b["asset"] not in ["USDT", "USDC", "BUSD"]:
            price = await binance_client.get_ticker_price(f"{b['asset']}USDT")
            usd_value = b["total"] * price
        
        balances.append(PortfolioBalance(
            asset=b["asset"],
            free=b["free"],
            locked=b["locked"],
            total=b["total"],
            usd_value=usd_value
        ))
    
    # If no exchange data, return demo balances for testing
    if not balances:
        balances = [
            PortfolioBalance(
                asset="USDT",
                free=10000.00,
                locked=0.00,
                total=10000.00,
                usd_value=10000.00
            )
        ]
    
    return balances

@app.get("/api/signals/recent", response_model=List[TradeSignal])
async def get_recent_signals(
    limit: int = 10,
    username: str = Depends(verify_token)
):
    # TODO: Integrate with actual signal database
    # For now, return empty list (signals will come from strategy engine)
    return []

@app.get("/api/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(username: str = Depends(verify_token)):
    # TODO: Calculate from actual trade history
    return PerformanceMetrics(
        total_pnl=0.0,
        total_pnl_pct=0.0,
        daily_pnl=0.0,
        daily_pnl_pct=0.0,
        win_rate=0.0,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        sharpe_ratio=0.0,
        max_drawdown=0.0
    )

@app.get("/api/trades/history")
async def get_trade_history(
    limit: int = 50,
    username: str = Depends(verify_token)
):
    # TODO: Integrate with actual trade database
    return {"trades": [], "total": 0}

@app.post("/api/bot/start")
async def start_bot(username: str = Depends(verify_token)):
    bot_state["is_running"] = True
    bot_state["last_update"] = datetime.utcnow()
    
    await manager.broadcast({
        "type": "bot_status",
        "data": {"is_running": True, "timestamp": datetime.utcnow().isoformat()}
    })
    return {"status": "success", "message": "Bot started"}

@app.post("/api/bot/stop")
async def stop_bot(username: str = Depends(verify_token)):
    bot_state["is_running"] = False
    bot_state["last_update"] = datetime.utcnow()
    
    await manager.broadcast({
        "type": "bot_status",
        "data": {"is_running": False, "timestamp": datetime.utcnow().isoformat()}
    })
    return {"status": "success", "message": "Bot stopped"}

@app.post("/api/bot/mode")
async def set_bot_mode(
    mode: str,
    username: str = Depends(verify_token)
):
    if mode not in ["auto", "manual", "semi-auto"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    bot_state["mode"] = mode
    bot_state["last_update"] = datetime.utcnow()
    
    await manager.broadcast({
        "type": "mode_change",
        "data": {"mode": mode, "timestamp": datetime.utcnow().isoformat()}
    })
    return {"status": "success", "message": f"Mode set to {mode}"}

@app.post("/api/bot/ai")
async def toggle_ai(
    enabled: bool,
    username: str = Depends(verify_token)
):
    bot_state["ai_enabled"] = enabled
    bot_state["last_update"] = datetime.utcnow()
    
    await manager.broadcast({
        "type": "ai_toggle",
        "data": {"ai_enabled": enabled, "timestamp": datetime.utcnow().isoformat()}
    })
    return {"status": "success", "message": f"AI {'enabled' if enabled else 'disabled'}"}

@app.get("/api/market/prices")
async def get_market_prices(symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT"):
    symbol_list = symbols.split(",")
    prices = {}
    
    for symbol in symbol_list:
        price = await binance_client.get_ticker_price(symbol.strip())
        prices[symbol.strip()] = price
    
    return {"prices": prices, "timestamp": datetime.utcnow().isoformat()}

# ========== WEBSOCKET ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                # Subscribe to price updates
                pass
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({
                    "type": "echo",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ========== HEALTH CHECK ==========

@app.get("/health")
async def health_check():
    exchanges_connected = []
    if BINANCE_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.binance.com/api/v3/ping", timeout=3.0)
                if response.status_code == 200:
                    exchanges_connected.append("binance")
        except:
            pass
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "exchanges_connected": exchanges_connected,
        "bot_running": bot_state["is_running"]
    }

# ========== STARTUP/SHUTDOWN ==========

@app.on_event("startup")
async def startup_event():
    print("Strategy Engine Pro API v2.0 starting...")
    print(f"API available at http://localhost:8000")
    print(f"API docs at http://localhost:8000/docs")
    print(f"Binance configured: {bool(BINANCE_API_KEY)}")
    print(f"Bitget configured: {bool(BITGET_API_KEY)}")

@app.on_event("shutdown")
async def shutdown_event():
    print("Strategy Engine Pro API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
