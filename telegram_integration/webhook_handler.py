"""
Telegram Webhook Handler

Provides real-time webhook endpoint for Telegram Bot API.
Replaces polling (getUpdates) with webhook for production deployment.

Features:
- FastAPI-based webhook endpoint
- Automatic webhook registration
- Request validation and security
- Integration with existing AlertManager
- Graceful error handling
- Health check endpoint

Usage:
    python telegram_integration/webhook_handler.py
    
    # Or with custom configuration
    webhook = TelegramWebhookHandler(
        webhook_url="https://yourdomain.com/webhook",
        port=8443
    )
    await webhook.start()

Requirements:
    pip install fastapi uvicorn python-telegram-bot
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn
from telegram import Update
from telegram.ext import Application

from .bot_config import get_bot_token, get_chat_id
from .alert_manager import AlertManager


logger = logging.getLogger(__name__)


class TelegramWebhookHandler:
    """
    Webhook-based Telegram bot handler for production deployment.
    
    Replaces polling with webhook for better performance and reliability.
    Integrates with existing AlertManager for signal notifications.
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        port: int = 8443,
        host: str = "0.0.0.0",
        webhook_path: str = "/webhook",
        alert_manager: Optional[AlertManager] = None
    ):
        """
        Initialize webhook handler
        
        Args:
            webhook_url: Public URL for webhook (e.g., https://yourdomain.com/webhook)
            port: Port to run server on (default: 8443, recommended for Telegram)
            host: Host to bind to (default: 0.0.0.0)
            webhook_path: Path for webhook endpoint (default: /webhook)
            alert_manager: Existing AlertManager instance (optional)
        """
        # Configuration
        self.webhook_url = webhook_url or os.getenv("TELEGRAM_WEBHOOK_URL")
        self.port = port
        self.host = host
        self.webhook_path = webhook_path
        
        # Telegram configuration
        self.bot_token = get_bot_token()
        self.chat_id = get_chat_id()
        
        # Components
        self.app: Optional[FastAPI] = None
        self.telegram_app: Optional[Application] = None
        self.alert_manager = alert_manager
        self.is_running = False
        
        # Validate configuration
        if not self.webhook_url:
            raise ValueError(
                "webhook_url must be provided or set TELEGRAM_WEBHOOK_URL env variable"
            )
        
        if not self.webhook_url.startswith("https://"):
            logger.warning(
                "Webhook URL should use HTTPS for security. "
                "HTTP webhooks will be rejected by Telegram in production."
            )
        
        logger.info(f"TelegramWebhookHandler initialized for {self.webhook_url}")
    
    def create_app(self) -> FastAPI:
        """
        Create FastAPI application with webhook endpoint.
        
        Returns:
            Configured FastAPI app
        """
        app = FastAPI(
            title="Telegram Webhook Handler",
            description="Real-time webhook endpoint for v0-strategy-engine-pro Telegram bot",
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            """Health check endpoint"""
            return {
                "status": "running",
                "service": "telegram-webhook",
                "webhook_configured": self.is_running
            }
        
        @app.get("/health")
        async def health_check():
            """Detailed health check"""
            return {
                "status": "healthy",
                "webhook_url": self.webhook_url,
                "bot_connected": self.telegram_app is not None,
                "alert_manager_active": self.alert_manager is not None
            }
        
        @app.post(self.webhook_path)
        async def webhook(request: Request):
            """Handle incoming webhook updates from Telegram"""
            try:
                # Parse update from request
                update_dict = await request.json()
                update = Update.de_json(update_dict, self.telegram_app.bot)
                
                # Process update
                await self.telegram_app.process_update(update)
                
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"ok": True}
                )
                
            except Exception as e:
                logger.error(f"Error processing webhook update: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process update"
                )
        
        return app
    
    async def setup_telegram_bot(self) -> None:
        """
        Initialize Telegram bot application and set webhook.
        """
        try:
            # Create telegram application
            self.telegram_app = (
                Application.builder()
                .token(self.bot_token)
                .build()
            )
            
            # Initialize bot
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            
            # Set webhook URL
            webhook_url_full = f"{self.webhook_url.rstrip('/')}{self.webhook_path}"
            
            logger.info(f"Setting webhook to: {webhook_url_full}")
            
            success = await self.telegram_app.bot.set_webhook(
                url=webhook_url_full,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            
            if success:
                logger.info("Webhook set successfully")
            else:
                raise RuntimeError("Failed to set webhook")
            
            # Verify webhook
            webhook_info = await self.telegram_app.bot.get_webhook_info()
            logger.info(f"Webhook info: {webhook_info}")
            
            if webhook_info.url != webhook_url_full:
                raise RuntimeError(
                    f"Webhook URL mismatch: expected {webhook_url_full}, "
                    f"got {webhook_info.url}"
                )
            
        except Exception as e:
            logger.error(f"Failed to setup Telegram bot: {e}", exc_info=True)
            raise
    
    async def start(self) -> None:
        """
        Start the webhook handler.
        
        This will:
        1. Create FastAPI app
        2. Setup Telegram bot and configure webhook
        3. Start uvicorn server
        """
        if self.is_running:
            logger.warning("Webhook handler already running")
            return
        
        try:
            # Create FastAPI app
            self.app = self.create_app()
            
            # Setup Telegram bot
            await self.setup_telegram_bot()
            
            # Mark as running
            self.is_running = True
            
            logger.info(f"Starting webhook server on {self.host}:{self.port}")
            
            # Start server
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start webhook handler: {e}", exc_info=True)
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """
        Stop the webhook handler and cleanup resources.
        """
        if not self.is_running:
            return
        
        try:
            # Delete webhook
            if self.telegram_app:
                logger.info("Deleting webhook")
                await self.telegram_app.bot.delete_webhook()
                
                # Stop telegram app
                await self.telegram_app.stop()
                await self.telegram_app.shutdown()
            
            self.is_running = False
            logger.info("Webhook handler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping webhook handler: {e}", exc_info=True)


# ========== SEGMENT 1 END ==========
# SEGMENT 2 will include:
# - Helper functions
# - Error handling utilities
# - Example usage
# - Integration with AlertManager      
