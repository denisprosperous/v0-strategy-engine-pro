"""
JWT Authentication - Phase 2.3c

Provides JWT token generation, validation, and refresh mechanisms.
Supports access tokens, refresh tokens, and token claims.

Author: Development Team
Date: 2024
Version: 2.3.0
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

try:
    import jwt
except ImportError:
    raise ImportError("PyJWT library required: pip install PyJWT")

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class JWTManager:
    """
    Manages JWT token generation, validation, and claims.
    
    Supports:
    - Access tokens (short-lived: 15 minutes)
    - Refresh tokens (long-lived: 30 days)
    - Custom claims and metadata
    - Token revocation tracking
    """
    
    # Token lifetimes
    ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRY = timedelta(days=30)
    API_KEY_EXPIRY = timedelta(days=365)
    
    # Algorithm
    ALGORITHM = "HS256"
    
    def __init__(self, secret_key: str):
        """
        Initialize JWT Manager.
        
        Args:
            secret_key: Secret key for signing tokens
        """
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        
        self.secret_key = secret_key
        self.revoked_tokens = set()  # In production, use Redis
    
    def generate_access_token(
        self,
        user_id: str,
        session_id: str,
        scopes: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate access token.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            scopes: Token scopes/permissions
            metadata: Additional metadata
        
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "token_type": TokenType.ACCESS.value,
            "scopes": scopes or ["read", "trade"],
            "iat": now,
            "exp": now + self.ACCESS_TOKEN_EXPIRY,
            "metadata": metadata or {}
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
            logger.debug(f"Access token generated for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            raise
    
    def generate_refresh_token(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """
        Generate refresh token.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "token_type": TokenType.REFRESH.value,
            "iat": now,
            "exp": now + self.REFRESH_TOKEN_EXPIRY
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
            logger.debug(f"Refresh token generated for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Refresh token generation failed: {e}")
            raise
    
    def generate_token_pair(
        self,
        user_id: str,
        session_id: str,
        scopes: Optional[list] = None
    ) -> Dict[str, str]:
        """
        Generate both access and refresh tokens.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            scopes: Token scopes
        
        Returns:
            Dictionary with access and refresh tokens
        """
        return {
            "access_token": self.generate_access_token(user_id, session_id, scopes),
            "refresh_token": self.generate_refresh_token(user_id, session_id),
            "token_type": "Bearer",
            "expires_in": int(self.ACCESS_TOKEN_EXPIRY.total_seconds())
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode token.
        
        Args:
            token: JWT token string
        
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Check revocation
            if token in self.revoked_tokens:
                logger.warning("Token has been revoked")
                return None
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
            logger.debug("Token verified successfully")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Refresh token string
        
        Returns:
            New token pair if valid, None otherwise
        """
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get("token_type") != TokenType.REFRESH.value:
            logger.warning("Invalid refresh token")
            return None
        
        return self.generate_token_pair(
            user_id=payload["user_id"],
            session_id=payload["session_id"]
        )
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke token (add to blacklist).
        
        Args:
            token: JWT token string
        
        Returns:
            True if revoked successfully
        """
        try:
            self.revoked_tokens.add(token)
            logger.info("Token revoked")
            return True
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    def revoke_session_tokens(self, session_id: str) -> int:
        """
        Revoke all tokens for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of tokens revoked
        """
        # In production, implement with database lookup
        logger.info(f"Revoking all tokens for session {session_id}")
        return 0
    
    def get_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get token claims without verification.
        
        Args:
            token: JWT token string
        
        Returns:
            Token claims if decodable
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.ALGORITHM],
                options={"verify_signature": False}
            )
            return payload
        except Exception as e:
            logger.warning(f"Could not decode token: {e}")
            return None


if __name__ == "__main__":
    # Example usage
    manager = JWTManager("your-secret-key-must-be-at-least-32-characters-long")
    
    # Generate tokens
    tokens = manager.generate_token_pair(
        user_id="user_123",
        session_id="session_456"
    )
    print(f"Access token: {tokens['access_token'][:20]}...")
    
    # Verify token
    verified = manager.verify_token(tokens["access_token"])
    print(f"Token verified: {verified is not None}")
    
    # Refresh token
    new_tokens = manager.refresh_access_token(tokens["refresh_token"])
    print(f"Tokens refreshed: {new_tokens is not None}")
