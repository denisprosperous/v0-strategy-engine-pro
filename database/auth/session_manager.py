"""
Session Manager - Phase 2.3a

Manages user sessions, session lifecycle, and session authentication.
Supports session creation, validation, renewal, and cleanup.

Author: Development Team
Date: 2024
Version: 2.3.0
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict, field

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


class SessionType(Enum):
    """Session type enumeration."""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    TRADING = "trading"


@dataclass
class SessionData:
    """Session data container."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_type: str = SessionType.WEB.value
    ip_address: str = ""
    user_agent: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = SessionStatus.ACTIVE.value
    metadata: Dict[str, Any] = field(default_factory=dict)
    refresh_count: int = 0
    is_secure: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid."""
        return (
            self.status == SessionStatus.ACTIVE.value and
            not self.is_expired()
        )


class SessionManager:
    """
    Manages user sessions with full lifecycle support.
    
    Responsibilities:
    - Create and maintain user sessions
    - Track session status and activity
    - Validate session authenticity
    - Handle session renewal and extension
    - Implement session cleanup and expiration
    - Support multi-device session management
    - Provide session history and audit trail
    """
    
    # Default session timeout: 24 hours
    DEFAULT_SESSION_TIMEOUT = timedelta(hours=24)
    
    # Refresh token timeout: 30 days
    REFRESH_TOKEN_TIMEOUT = timedelta(days=30)
    
    # Inactivity timeout: 2 hours
    INACTIVITY_TIMEOUT = timedelta(hours=2)
    
    # Maximum sessions per user
    MAX_SESSIONS_PER_USER = 5
    
    def __init__(self, db_session: Optional[DBSession] = None):
        """
        Initialize Session Manager.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.sessions_cache: Dict[str, SessionData] = {}
        
    def create_session(
        self,
        user_id: str,
        session_type: str = SessionType.WEB.value,
        ip_address: str = "",
        user_agent: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[timedelta] = None
    ) -> SessionData:
        """
        Create new user session.
        
        Args:
            user_id: User identifier
            session_type: Type of session (web, mobile, api, trading)
            ip_address: Client IP address
            user_agent: Client user agent string
            metadata: Additional session metadata
            timeout: Custom session timeout
        
        Returns:
            Created SessionData object
        """
        session_timeout = timeout or self.DEFAULT_SESSION_TIMEOUT
        
        session = SessionData(
            user_id=user_id,
            session_type=session_type,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + session_timeout,
            metadata=metadata or {},
            status=SessionStatus.ACTIVE.value
        )
        
        self.sessions_cache[session.session_id] = session
        logger.info(f"Session created: {session.session_id} for user {user_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            SessionData if found, None otherwise
        """
        session = self.sessions_cache.get(session_id)
        
        if session and session.is_valid():
            session.last_activity = datetime.utcnow()
            return session
        
        if session:
            self._mark_expired(session_id)
        
        return None
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate session authenticity and status.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session is valid
        """
        session = self.sessions_cache.get(session_id)
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False
        
        if not session.is_valid():
            logger.warning(f"Session invalid or expired: {session_id}")
            return False
        
        # Check inactivity
        inactive_duration = datetime.utcnow() - session.last_activity
        if inactive_duration > self.INACTIVITY_TIMEOUT:
            self._mark_expired(session_id)
            logger.warning(f"Session marked expired due to inactivity: {session_id}")
            return False
        
        return True
    
    def refresh_session(
        self,
        session_id: str,
        extend_timeout: Optional[timedelta] = None
    ) -> Optional[SessionData]:
        """
        Refresh and extend session.
        
        Args:
            session_id: Session identifier
            extend_timeout: Additional timeout to add
        
        Returns:
            Updated SessionData if successful
        """
        session = self.sessions_cache.get(session_id)
        
        if not session or not session.is_valid():
            logger.warning(f"Cannot refresh invalid session: {session_id}")
            return None
        
        extension = extend_timeout or self.DEFAULT_SESSION_TIMEOUT
        session.expires_at = datetime.utcnow() + extension
        session.last_activity = datetime.utcnow()
        session.refresh_count += 1
        
        logger.info(f"Session refreshed: {session_id} (count: {session.refresh_count})")
        
        return session
    
    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke (invalidate) session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if revoked successfully
        """
        session = self.sessions_cache.get(session_id)
        
        if not session:
            return False
        
        session.status = SessionStatus.REVOKED.value
        logger.info(f"Session revoked: {session_id}")
        
        return True
    
    def revoke_user_sessions(self, user_id: str, exclude_session_id: Optional[str] = None) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User identifier
            exclude_session_id: Session ID to exclude from revocation
        
        Returns:
            Number of sessions revoked
        """
        revoked_count = 0
        
        for session_id, session in list(self.sessions_cache.items()):
            if (
                session.user_id == user_id and
                session_id != exclude_session_id
            ):
                self.revoke_session(session_id)
                revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
        
        return revoked_count
    
    def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of active SessionData objects
        """
        sessions = [
            session for session in self.sessions_cache.values()
            if session.user_id == user_id and session.is_valid()
        ]
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from cache.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_ids = [
            session_id for session_id, session in self.sessions_cache.items()
            if session.is_expired()
        ]
        
        for session_id in expired_ids:
            del self.sessions_cache[session_id]
        
        logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
        
        return len(expired_ids)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        active_sessions = [s for s in self.sessions_cache.values() if s.is_valid()]
        
        return {
            "total_sessions": len(self.sessions_cache),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(self.sessions_cache) - len(active_sessions),
            "web_sessions": len([s for s in active_sessions if s.session_type == SessionType.WEB.value]),
            "mobile_sessions": len([s for s in active_sessions if s.session_type == SessionType.MOBILE.value]),
            "api_sessions": len([s for s in active_sessions if s.session_type == SessionType.API.value]),
            "trading_sessions": len([s for s in active_sessions if s.session_type == SessionType.TRADING.value]),
        }
    
    def _mark_expired(self, session_id: str) -> None:
        """
        Mark session as expired.
        
        Args:
            session_id: Session identifier
        """
        session = self.sessions_cache.get(session_id)
        if session:
            session.status = SessionStatus.EXPIRED.value
            logger.debug(f"Session marked as expired: {session_id}")


class SessionValidator:
    """
    Validates session integrity and security.
    """
    
    @staticmethod
    def validate_user_context(
        session: SessionData,
        ip_address: str,
        user_agent: str,
        strict: bool = False
    ) -> bool:
        """
        Validate session user context (IP, user-agent).
        
        Args:
            session: SessionData object
            ip_address: Current IP address
            user_agent: Current user agent
            strict: Enable strict validation
        
        Returns:
            True if context matches
        """
        if strict:
            # Strict mode: IP and user-agent must match exactly
            return (
                session.ip_address == ip_address and
                session.user_agent == user_agent
            )
        else:
            # Lenient mode: Just verify IP matches
            return session.ip_address == ip_address
    
    @staticmethod
    def check_suspicious_activity(
        session: SessionData,
        ip_address: str,
        current_time: datetime
    ) -> bool:
        """
        Check for suspicious session activity.
        
        Args:
            session: SessionData object
            ip_address: Current IP address
            current_time: Current timestamp
        
        Returns:
            True if suspicious activity detected
        """
        # Check for impossible travel (rapid location changes)
        time_since_activity = (current_time - session.last_activity).total_seconds()
        
        # If IP changed and activity within 10 seconds, mark suspicious
        if session.ip_address != ip_address and time_since_activity < 10:
            return True
        
        return False


if __name__ == "__main__":
    # Example usage
    manager = SessionManager()
    
    # Create session
    session = manager.create_session(
        user_id="user_123",
        session_type=SessionType.WEB.value,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0..."
    )
    
    print(f"Created session: {session.session_id}")
    print(f"Session valid: {manager.validate_session(session.session_id)}")
    print(f"Session stats: {manager.get_session_stats()}")
