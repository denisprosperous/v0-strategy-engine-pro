from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging
from typing import Optional

# Import models to ensure they are registered
from .models import (
    User, Strategy, Trade, TradeSignal, TradeExecution, 
    PerformanceMetrics, SocialTrade, MarketDataCache
)

# Create declarative base
Base = declarative_base()

# Database configuration
DATABASE_URL = "sqlite:///strategy_engine.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Logger
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database and create all tables"""
    try:
        # Import all models to ensure they are registered
        from .models import (
            User, Strategy, Trade, TradeSignal, TradeExecution, 
            PerformanceMetrics, SocialTrade, MarketDataCache
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        
        # Create default data if needed
        create_default_data()
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def create_default_data():
    """Create default data for the application"""
    try:
        db = SessionLocal()
        
        # Check if default data already exists
        existing_user = db.query(User).first()
        if existing_user:
            logger.info("Default data already exists, skipping creation")
            return
        
        # Create default user
        default_user = User(
            username="admin",
            email="admin@strategyenginepro.com",
            is_active=True,
            is_admin=True
        )
        db.add(default_user)
        
        # Create default strategy
        default_strategy = Strategy(
            name="Default Strategy",
            description="Default trading strategy",
            user_id=1,
            is_active=True,
            parameters={
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "bb_period": 20,
                "bb_std": 2.0
            }
        )
        db.add(default_strategy)
        
        # Commit changes
        db.commit()
        logger.info("Default data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_db():
    """Reset the database (drop all tables and recreate)"""
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
        
        # Recreate all tables
        init_db()
        logger.info("Database reset completed")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise

def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_db_info() -> dict:
    """Get database information"""
    try:
        db = SessionLocal()
        
        # Get table counts
        user_count = db.query(User).count()
        strategy_count = db.query(Strategy).count()
        trade_count = db.query(Trade).count()
        signal_count = db.query(TradeSignal).count()
        
        db.close()
        
        return {
            "database_url": DATABASE_URL,
            "connection_status": "connected" if check_db_connection() else "disconnected",
            "table_counts": {
                "users": user_count,
                "strategies": strategy_count,
                "trades": trade_count,
                "signals": signal_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            "database_url": DATABASE_URL,
            "connection_status": "error",
            "error": str(e)
        }

def backup_database(backup_path: str):
    """Create a backup of the database"""
    try:
        import shutil
        import os
        
        # Create backup directory if it doesn't exist
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copy database file
        shutil.copy2("strategy_engine.db", backup_path)
        logger.info(f"Database backed up to {backup_path}")
        
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        raise

def restore_database(backup_path: str):
    """Restore database from backup"""
    try:
        import shutil
        import os
        
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Close all connections
        engine.dispose()
        
        # Restore database file
        shutil.copy2(backup_path, "strategy_engine.db")
        logger.info(f"Database restored from {backup_path}")
        
        # Reinitialize connection
        global SessionLocal
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        raise

def optimize_database():
    """Optimize database performance"""
    try:
        db = SessionLocal()
        
        # SQLite specific optimizations
        if "sqlite" in DATABASE_URL:
            db.execute("VACUUM")
            db.execute("ANALYZE")
            db.commit()
            logger.info("Database optimized (VACUUM and ANALYZE)")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")

def create_indexes():
    """Create database indexes for better performance"""
    try:
        db = SessionLocal()
        
        # Create indexes for common queries
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp 
            ON trades (symbol, timestamp)
        """)
        
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_user_id 
            ON trades (user_id)
        """)
        
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp 
            ON trade_signals (symbol, timestamp)
        """)
        
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_user_id_date 
            ON performance_metrics (user_id, date)
        """)
        
        db.commit()
        logger.info("Database indexes created")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        db.rollback()
    finally:
        db.close()

def cleanup_old_data(days_to_keep: int = 90):
    """Clean up old data to maintain database performance"""
    try:
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Delete old market data cache
        deleted_cache = db.query(MarketDataCache).filter(
            MarketDataCache.timestamp < cutoff_date
        ).delete()
        
        # Delete old performance metrics
        deleted_metrics = db.query(PerformanceMetrics).filter(
            PerformanceMetrics.date < cutoff_date.date()
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_cache} cache entries and {deleted_metrics} metrics older than {days_to_keep} days")
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        db.rollback()
    finally:
        db.close()

# Database health check
def health_check() -> dict:
    """Perform a comprehensive database health check"""
    try:
        health_status = {
            "status": "healthy",
            "connection": check_db_connection(),
            "tables": {},
            "performance": {},
            "errors": []
        }
        
        if not health_status["connection"]:
            health_status["status"] = "unhealthy"
            health_status["errors"].append("Database connection failed")
            return health_status
        
        db = SessionLocal()
        
        # Check table health
        tables = ["users", "strategies", "trades", "trade_signals", "performance_metrics"]
        for table in tables:
            try:
                result = db.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                health_status["tables"][table] = {
                    "exists": True,
                    "record_count": count
                }
            except Exception as e:
                health_status["tables"][table] = {
                    "exists": False,
                    "error": str(e)
                }
                health_status["errors"].append(f"Table {table} error: {e}")
        
        # Check database size
        try:
            import os
            db_size = os.path.getsize("strategy_engine.db")
            health_status["performance"]["database_size_mb"] = round(db_size / (1024 * 1024), 2)
        except Exception as e:
            health_status["performance"]["database_size_mb"] = "unknown"
            health_status["errors"].append(f"Could not get database size: {e}")
        
        db.close()
        
        # Update overall status
        if health_status["errors"]:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": False,
            "error": str(e)
        }
