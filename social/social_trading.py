import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

from database.models import SocialTrade, Trade, User
from database.database import SessionLocal
from trading.mode_manager import TradingModeManager

class SignalVisibility(Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    FOLLOWERS = "followers"

@dataclass
class SocialSignal:
    """Social trading signal"""
    id: str
    user_id: int
    username: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    description: str
    visibility: SignalVisibility
    timestamp: datetime
    followers_count: int
    success_rate: float
    total_pnl: float

class SocialTradingManager:
    """Manages social trading features"""
    
    def __init__(self, trading_manager: TradingModeManager):
        self.trading_manager = trading_manager
        self.logger = logging.getLogger(__name__)
        
        # Social trading state
        self.following_users = {}  # user_id -> following_info
        self.signal_subscribers = {}  # signal_id -> subscribers
        self.copied_trades = {}  # trade_id -> copy_info
    
    async def share_signal(self, user_id: int, signal_data: Dict) -> str:
        """Share a trading signal with the community"""
        try:
            db = SessionLocal()
            
            # Create social signal
            signal_id = f"signal_{user_id}_{datetime.now().timestamp()}"
            
            # Get user info
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Create social signal object
            social_signal = SocialSignal(
                id=signal_id,
                user_id=user_id,
                username=user.username,
                symbol=signal_data['symbol'],
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                take_profit=signal_data['take_profit'],
                confidence=signal_data['confidence'],
                description=signal_data['description'],
                visibility=SignalVisibility(signal_data.get('visibility', 'public')),
                timestamp=datetime.now(),
                followers_count=0,
                success_rate=0.0,
                total_pnl=0.0
            )
            
            # Store in database (simplified)
            # In a real implementation, this would be stored in a proper table
            
            self.logger.info(f"Signal shared by {user.username}: {signal_data['symbol']} {signal_data['direction']}")
            
            return signal_id
            
        except Exception as e:
            self.logger.error(f"Error sharing signal: {e}")
            raise
        finally:
            db.close()
    
    async def follow_user(self, follower_id: int, user_to_follow_id: int) -> bool:
        """Follow a user for social trading"""
        try:
            db = SessionLocal()
            
            # Check if user exists
            user_to_follow = db.query(User).filter(User.id == user_to_follow_id).first()
            if not user_to_follow:
                raise ValueError("User to follow not found")
            
            # Check if already following
            if follower_id in self.following_users and user_to_follow_id in self.following_users[follower_id]:
                return True
            
            # Add to following list
            if follower_id not in self.following_users:
                self.following_users[follower_id] = {}
            
            self.following_users[follower_id][user_to_follow_id] = {
                'since': datetime.now(),
                'auto_copy': False,
                'copy_percentage': 0.0
            }
            
            self.logger.info(f"User {follower_id} started following {user_to_follow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error following user: {e}")
            return False
        finally:
            db.close()
    
    async def unfollow_user(self, follower_id: int, user_to_unfollow_id: int) -> bool:
        """Unfollow a user"""
        try:
            if follower_id in self.following_users:
                if user_to_unfollow_id in self.following_users[follower_id]:
                    del self.following_users[follower_id][user_to_unfollow_id]
                    self.logger.info(f"User {follower_id} unfollowed {user_to_unfollow_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error unfollowing user: {e}")
            return False
    
    async def copy_trade(self, copier_id: int, original_trade_id: int, copy_percentage: float = 1.0) -> bool:
        """Copy a trade from another user"""
        try:
            db = SessionLocal()
            
            # Get original trade
            original_trade = db.query(Trade).filter(Trade.id == original_trade_id).first()
            if not original_trade:
                raise ValueError("Original trade not found")
            
            # Check if user is following the original trader
            if not self.is_following(copier_id, original_trade.user_id):
                raise ValueError("Must follow user to copy their trades")
            
            # Calculate copy amount
            copy_amount = original_trade.amount * copy_percentage
            
            # Execute copy trade
            success = await self.trading_manager.manual_trade(
                symbol=original_trade.symbol,
                side=original_trade.side,
                amount=copy_amount,
                price=original_trade.price
            )
            
            if success:
                # Record social trade
                social_trade = SocialTrade(
                    original_trade_id=original_trade_id,
                    copied_by_user_id=copier_id,
                    status='executed',
                    copied_at=datetime.now()
                )
                db.add(social_trade)
                db.commit()
                
                self.logger.info(f"Trade copied: {copier_id} copied {original_trade_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error copying trade: {e}")
            return False
        finally:
            db.close()
    
    async def get_following_signals(self, user_id: int, limit: int = 20) -> List[SocialSignal]:
        """Get signals from users being followed"""
        try:
            if user_id not in self.following_users:
                return []
            
            following_users = list(self.following_users[user_id].keys())
            
            # Get recent signals from followed users
            db = SessionLocal()
            recent_trades = db.query(Trade).filter(
                Trade.user_id.in_(following_users),
                Trade.timestamp >= datetime.now() - timedelta(hours=24)
            ).order_by(Trade.timestamp.desc()).limit(limit).all()
            
            signals = []
            for trade in recent_trades:
                user = db.query(User).filter(User.id == trade.user_id).first()
                if user:
                    signal = SocialSignal(
                        id=f"signal_{trade.id}",
                        user_id=trade.user_id,
                        username=user.username,
                        symbol=trade.symbol,
                        direction=trade.side,
                        entry_price=trade.price,
                        stop_loss=trade.price * 0.98,  # Default 2% stop loss
                        take_profit=trade.price * 1.06,  # Default 6% take profit
                        confidence=0.7,  # Default confidence
                        description=f"Trade by {user.username}",
                        visibility=SignalVisibility.FOLLOWERS,
                        timestamp=trade.timestamp,
                        followers_count=0,
                        success_rate=0.0,
                        total_pnl=0.0
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting following signals: {e}")
            return []
        finally:
            db.close()
    
    async def get_public_signals(self, limit: int = 20) -> List[SocialSignal]:
        """Get public signals from the community"""
        try:
            db = SessionLocal()
            
            # Get recent public trades
            recent_trades = db.query(Trade).filter(
                Trade.timestamp >= datetime.now() - timedelta(hours=24)
            ).order_by(Trade.timestamp.desc()).limit(limit).all()
            
            signals = []
            for trade in recent_trades:
                user = db.query(User).filter(User.id == trade.user_id).first()
                if user:
                    # Calculate user success rate
                    user_trades = db.query(Trade).filter(Trade.user_id == trade.user_id).all()
                    success_rate = len([t for t in user_trades if t.pnl and t.pnl > 0]) / len(user_trades) if user_trades else 0
                    
                    signal = SocialSignal(
                        id=f"signal_{trade.id}",
                        user_id=trade.user_id,
                        username=user.username,
                        symbol=trade.symbol,
                        direction=trade.side,
                        entry_price=trade.price,
                        stop_loss=trade.price * 0.98,
                        take_profit=trade.price * 1.06,
                        confidence=0.7,
                        description=f"Public trade by {user.username}",
                        visibility=SignalVisibility.PUBLIC,
                        timestamp=trade.timestamp,
                        followers_count=0,
                        success_rate=success_rate,
                        total_pnl=sum(t.pnl or 0 for t in user_trades)
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting public signals: {e}")
            return []
        finally:
            db.close()
    
    def is_following(self, follower_id: int, user_id: int) -> bool:
        """Check if user is following another user"""
        return (follower_id in self.following_users and 
                user_id in self.following_users[follower_id])
    
    async def set_auto_copy(self, follower_id: int, user_id: int, enabled: bool, percentage: float = 1.0):
        """Enable/disable automatic copying of trades"""
        try:
            if not self.is_following(follower_id, user_id):
                raise ValueError("Must follow user to set auto-copy")
            
            self.following_users[follower_id][user_id]['auto_copy'] = enabled
            self.following_users[follower_id][user_id]['copy_percentage'] = percentage
            
            self.logger.info(f"Auto-copy {'enabled' if enabled else 'disabled'} for {follower_id} following {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error setting auto-copy: {e}")
            raise
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get social trading statistics for a user"""
        try:
            db = SessionLocal()
            
            # Get user's trades
            user_trades = db.query(Trade).filter(Trade.user_id == user_id).all()
            
            # Calculate statistics
            total_trades = len(user_trades)
            winning_trades = len([t for t in user_trades if t.pnl and t.pnl > 0])
            success_rate = winning_trades / total_trades if total_trades > 0 else 0
            total_pnl = sum(t.pnl or 0 for t in user_trades)
            
            # Get followers count
            followers_count = sum(1 for following in self.following_users.values() 
                                if user_id in following)
            
            # Get copied trades count
            copied_trades = db.query(SocialTrade).filter(
                SocialTrade.original_trade_id.in_([t.id for t in user_trades])
            ).count()
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'success_rate': success_rate,
                'total_pnl': total_pnl,
                'followers_count': followers_count,
                'copied_trades_count': copied_trades,
                'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user stats: {e}")
            return {}
        finally:
            db.close()
    
    async def get_leaderboard(self, period: str = "1m") -> List[Dict[str, Any]]:
        """Get social trading leaderboard"""
        try:
            db = SessionLocal()
            
            # Calculate start date
            start_date = datetime.now() - timedelta(days=30 if period == "1m" else 7 if period == "1w" else 365)
            
            # Get all users with trades in period
            users_with_trades = db.query(Trade.user_id).filter(
                Trade.timestamp >= start_date
            ).distinct().all()
            
            leaderboard = []
            for (user_id,) in users_with_trades:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    continue
                
                # Get user's trades in period
                user_trades = db.query(Trade).filter(
                    Trade.user_id == user_id,
                    Trade.timestamp >= start_date
                ).all()
                
                # Calculate metrics
                total_pnl = sum(t.pnl or 0 for t in user_trades)
                success_rate = len([t for t in user_trades if t.pnl and t.pnl > 0]) / len(user_trades) if user_trades else 0
                followers_count = sum(1 for following in self.following_users.values() if user_id in following)
                
                leaderboard.append({
                    'user_id': user_id,
                    'username': user.username,
                    'total_pnl': total_pnl,
                    'success_rate': success_rate,
                    'followers_count': followers_count,
                    'trade_count': len(user_trades)
                })
            
            # Sort by total PnL
            leaderboard.sort(key=lambda x: x['total_pnl'], reverse=True)
            
            return leaderboard[:20]  # Top 20
            
        except Exception as e:
            self.logger.error(f"Error getting leaderboard: {e}")
            return []
        finally:
            db.close()
    
    async def get_signal_analytics(self, signal_id: str) -> Dict[str, Any]:
        """Get analytics for a specific signal"""
        try:
            db = SessionLocal()
            
            # Parse signal ID to get trade ID
            if signal_id.startswith("signal_"):
                trade_id = int(signal_id.split("_")[1])
            else:
                trade_id = int(signal_id)
            
            # Get original trade
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                return {}
            
            # Get copied trades
            copied_trades = db.query(SocialTrade).filter(
                SocialTrade.original_trade_id == trade_id
            ).all()
            
            # Calculate analytics
            copy_count = len(copied_trades)
            successful_copies = len([ct for ct in copied_trades if ct.status == 'executed'])
            
            return {
                'original_trade': {
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'amount': trade.amount,
                    'price': trade.price,
                    'pnl': trade.pnl,
                    'timestamp': trade.timestamp.isoformat()
                },
                'copy_analytics': {
                    'total_copies': copy_count,
                    'successful_copies': successful_copies,
                    'copy_success_rate': successful_copies / copy_count if copy_count > 0 else 0,
                    'total_copied_pnl': sum(ct.execution_pnl or 0 for ct in copied_trades)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting signal analytics: {e}")
            return {}
        finally:
            db.close()

class SocialTradingNotifier:
    """Handles notifications for social trading events"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.notification_callbacks = []
    
    def add_notification_callback(self, callback):
        """Add notification callback"""
        self.notification_callbacks.append(callback)
    
    async def notify_signal_shared(self, signal: SocialSignal):
        """Notify when a signal is shared"""
        message = f"📡 New signal shared by {signal.username}: {signal.symbol} {signal.direction.upper()}"
        
        for callback in self.notification_callbacks:
            try:
                await callback(message)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {e}")
    
    async def notify_trade_copied(self, copier_id: int, original_trade_id: int):
        """Notify when a trade is copied"""
        message = f"📋 Trade {original_trade_id} copied by user {copier_id}"
        
        for callback in self.notification_callbacks:
            try:
                await callback(message)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {e}")
    
    async def notify_new_follower(self, follower_id: int, user_id: int):
        """Notify when someone follows a user"""
        message = f"👥 User {follower_id} started following user {user_id}"
        
        for callback in self.notification_callbacks:
            try:
                await callback(message)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {e}")
