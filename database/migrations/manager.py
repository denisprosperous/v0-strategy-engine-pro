"""
Database Migration Manager - Phase 2.2

Provides unified interface for database migrations using Alembic.
Supports version tracking, migration history, and automatic schema generation.

Author: Development Team
Date: 2024
Version: 2.2.0
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, MetaData, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationDirection(Enum):
    """Migration direction enumeration."""
    UP = "upgrade"
    DOWN = "downgrade"


class MigrationManager:
    """
    Unified database migration manager using Alembic backend.
    
    Responsibilities:
    - Manage database schema migrations
    - Track migration history
    - Provide version management
    - Support for auto-generating migrations from model changes
    - Handle rollback and downgrade operations
    - Generate and execute SQL migrations
    """
    
    def __init__(self, database_url: str, migrations_path: Optional[str] = None):
        """
        Initialize Migration Manager.
        
        Args:
            database_url: SQLAlchemy database URL
            migrations_path: Path to migrations directory (default: ./migrations)
        """
        self.database_url = database_url
        self.migrations_path = Path(migrations_path or "database/migrations")
        self.engine: Optional[Engine] = None
        self.alembic_config = self._init_alembic_config()
        self.metadata = MetaData()
        
    def _init_alembic_config(self) -> Config:
        """
        Initialize Alembic configuration.
        
        Returns:
            Configured Alembic Config object
        """
        alembic_ini = self.migrations_path.parent / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning(f"alembic.ini not found at {alembic_ini}")
        
        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", self.database_url)
        config.set_main_option("script_location", str(self.migrations_path))
        return config
    
    def connect(self) -> Engine:
        """
        Create database connection engine.
        
        Returns:
            SQLAlchemy Engine instance
        """
        if self.engine is None:
            self.engine = create_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        return self.engine
    
    def get_current_version(self) -> str:
        """
        Get current database schema version.
        
        Returns:
            Current revision identifier
        """
        engine = self.connect()
        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            current_version = migration_context.get_current_revision()
        return current_version or "<base>"
    
    def get_all_versions(self) -> List[Dict[str, Any]]:
        """
        Get list of all available migration versions.
        
        Returns:
            List of migration version information
        """
        script = ScriptDirectory.from_config(self.alembic_config)
        versions = []
        
        for sc in script.walk_revisions("base", "heads"):
            versions.append({
                "revision": sc.revision,
                "down_revision": sc.down_revision,
                "message": sc.message,
                "timestamp": datetime.now().isoformat()
            })
        
        return versions
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration execution history from database.
        
        Returns:
            List of executed migrations
        """
        engine = self.connect()
        history = []
        
        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text("SELECT * FROM alembic_version ORDER BY version_num")
                )
                for row in result:
                    history.append({
                        "version": row[0],
                        "executed_at": datetime.now().isoformat()
                    })
        except Exception as e:
            logger.warning(f"Could not retrieve migration history: {e}")
        
        return history
    
    def is_database_initialized(self) -> bool:
        """
        Check if database is initialized for migrations.
        
        Returns:
            True if alembic_version table exists
        """
        engine = self.connect()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return "alembic_version" in tables
    
    def init_database(self) -> bool:
        """
        Initialize database migration tracking (create alembic_version table).
        
        Returns:
            True if initialization successful
        """
        if self.is_database_initialized():
            logger.info("Database already initialized for migrations")
            return True
        
        engine = self.connect()
        try:
            with engine.connect() as connection:
                connection.execute(
                    text("""
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    """)
                )
                connection.commit()
                logger.info("Database migration table created")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def get_table_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about database tables.
        
        Args:
            table_name: Specific table name (None = all tables)
        
        Returns:
            Dictionary with table structure information
        """
        engine = self.connect()
        inspector = inspect(engine)
        
        if table_name:
            return {
                "columns": inspector.get_columns(table_name),
                "primary_keys": inspector.get_pk_constraint(table_name),
                "foreign_keys": inspector.get_foreign_keys(table_name),
                "indexes": inspector.get_indexes(table_name)
            }
        else:
            tables = inspector.get_table_names()
            return {table: self.get_table_info(table) for table in tables}
    
    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate database schema against requirements.
        
        Returns:
            Validation results
        """
        engine = self.connect()
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        
        # Check for required tables (from models_v2.py)
        required_tables = [
            "users", "user_sessions", "assets", "market_data",
            "strategies", "signals", "trades", "performance_metrics"
        ]
        
        missing_tables = [t for t in required_tables if t not in tables]
        
        return {
            "valid": len(missing_tables) == 0,
            "total_tables": len(tables),
            "tables": tables,
            "missing_tables": missing_tables,
            "required_tables": required_tables
        }
    
    def close(self) -> None:
        """
        Close database connection.
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("Database connection closed")


class MigrationExecutor:
    """
    Executes database migrations using Alembic.
    
    Handles upgrade, downgrade, and migration status tracking.
    """
    
    def __init__(self, manager: MigrationManager):
        """
        Initialize Migration Executor.
        
        Args:
            manager: MigrationManager instance
        """
        self.manager = manager
    
    def upgrade(self, target_version: str = "head") -> bool:
        """
        Upgrade database to target migration version.
        
        Args:
            target_version: Target revision (default: head)
        
        Returns:
            True if upgrade successful
        """
        try:
            from alembic.command import upgrade
            logger.info(f"Upgrading database to {target_version}")
            upgrade(self.manager.alembic_config, target_version)
            logger.info("Upgrade completed successfully")
            return True
        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return False
    
    def downgrade(self, target_version: str) -> bool:
        """
        Downgrade database to target migration version.
        
        Args:
            target_version: Target revision
        
        Returns:
            True if downgrade successful
        """
        try:
            from alembic.command import downgrade
            logger.info(f"Downgrading database to {target_version}")
            downgrade(self.manager.alembic_config, target_version)
            logger.info("Downgrade completed successfully")
            return True
        except Exception as e:
            logger.error(f"Downgrade failed: {e}")
            return False
    
    def generate_migration(self, message: str, autogenerate: bool = True) -> bool:
        """
        Generate new migration from model changes.
        
        Args:
            message: Migration description
            autogenerate: Auto-detect changes from models
        
        Returns:
            True if migration generated successfully
        """
        try:
            from alembic.command import revision
            logger.info(f"Generating migration: {message}")
            revision(
                self.manager.alembic_config,
                message=message,
                autogenerate=autogenerate
            )
            logger.info("Migration generated successfully")
            return True
        except Exception as e:
            logger.error(f"Migration generation failed: {e}")
            return False


class MigrationValidator:
    """
    Validates migration integrity and compatibility.
    """
    
    @staticmethod
    def validate_migrations_directory(migrations_path: Path) -> bool:
        """
        Validate migrations directory structure.
        
        Args:
            migrations_path: Path to migrations directory
        
        Returns:
            True if directory structure is valid
        """
        required_files = ["env.py", "script.py.mako"]
        required_dirs = ["versions"]
        
        for file in required_files:
            if not (migrations_path / file).exists():
                logger.warning(f"Missing required file: {file}")
                return False
        
        for dir in required_dirs:
            if not (migrations_path / dir).exists():
                logger.warning(f"Missing required directory: {dir}")
                return False
        
        return True
    
    @staticmethod
    def check_migration_compatibility(from_version: str, to_version: str) -> bool:
        """
        Check if migration path is compatible (simplified check).
        
        Args:
            from_version: Starting version
            to_version: Target version
        
        Returns:
            True if migration path is compatible
        """
        # In production, implement comprehensive compatibility checks
        return True


# Module initialization
if __name__ == "__main__":
    # Example usage
    db_url = "postgresql://user:password@localhost/trading_db"
    manager = MigrationManager(db_url)
    
    print(f"Current version: {manager.get_current_version()}")
    print(f"Database initialized: {manager.is_database_initialized()}")
    print(f"Schema valid: {manager.validate_schema()['valid']}")
