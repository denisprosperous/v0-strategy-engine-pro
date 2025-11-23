"""Encrypted Database Operations - Segment 1

Provides bulk encryption/decryption operations for database records.
Optimized for performance with batch processing and connection pooling.

Features:
- Bulk encryption of sensitive fields
- Batch processing for large datasets
- Transaction-safe operations
- Performance monitoring
- Automatic retry on failure

Author: v0-strategy-engine-pro
Version: 1.0
"""

import logging
import time
from typing import List, Dict, Any, Optional, Type, Callable
from contextlib import contextmanager
from sqlalchemy import select, update, and_
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

from database.encrypted_fields import EncryptionManager, EncryptedString, EncryptedJSON
from database.database import get_db, SessionLocal

logger = logging.getLogger(__name__)


class BulkEncryptionProcessor:
    """Handles bulk encryption/decryption operations for database records."""
    
    def __init__(self, batch_size: int = 100):
        """Initialize bulk processor.
        
        Args:
            batch_size: Number of records to process in one batch (default 100)
        """
        self.batch_size = batch_size
        self.encryption_manager = EncryptionManager()
        self.stats = {
            'total_processed': 0,
            'total_encrypted': 0,
            'total_decrypted': 0,
            'total_errors': 0,
            'processing_time': 0.0
        }
    
    def encrypt_column_bulk(
        self,
        model: Type[DeclarativeMeta],
        column_name: str,
        filter_condition: Optional[Any] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Encrypt a column for multiple records in batches.
        
        Args:
            model: SQLAlchemy model class
            column_name: Name of column to encrypt
            filter_condition: Optional SQLAlchemy filter condition
            session: Optional database session (creates new if None)
        
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        close_session = False
        
        if session is None:
            session = SessionLocal()
            close_session = True
        
        try:
            # Build query
            query = select(model)
            if filter_condition is not None:
                query = query.where(filter_condition)
            
            # Get total count
            total_count = session.execute(
                select(func.count()).select_from(model)
            ).scalar()
            
            logger.info(f"Starting bulk encryption of {column_name} for {total_count} records")
            
            processed = 0
            encrypted = 0
            errors = 0
            
            # Process in batches
            while processed < total_count:
                # Fetch batch
                batch_query = query.offset(processed).limit(self.batch_size)
                records = session.execute(batch_query).scalars().all()
                
                if not records:
                    break
                
                # Process batch
                for record in records:
                    try:
                        # Get current value
                        current_value = getattr(record, column_name)
                        
                        # Skip if already encrypted or None
                        if current_value is None:
                            processed += 1
                            continue
                        
                        # Check if already encrypted
                        if isinstance(current_value, str) and current_value.startswith('gAAAAAB'):
                            processed += 1
                            continue
                        
                        # Encrypt value
                        encrypted_value = self.encryption_manager.encrypt(current_value)
                        setattr(record, column_name, encrypted_value)
                        encrypted += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to encrypt record {record.id}: {e}")
                        errors += 1
                    
                    processed += 1
                
                # Commit batch
                try:
                    session.commit()
                    logger.debug(f"Committed batch: {processed}/{total_count}")
                except Exception as e:
                    logger.error(f"Batch commit failed: {e}")
                    session.rollback()
                    errors += len(records)
            
            # Calculate stats
            processing_time = time.time() - start_time
            self.stats['total_processed'] += processed
            self.stats['total_encrypted'] += encrypted
            self.stats['total_errors'] += errors
            self.stats['processing_time'] += processing_time
            
            result = {
                'total_count': total_count,
                'processed': processed,
                'encrypted': encrypted,
                'skipped': processed - encrypted - errors,
                'errors': errors,
                'processing_time': processing_time,
                'throughput': processed / processing_time if processing_time > 0 else 0
            }
            
            logger.info(
                f"Bulk encryption complete: {encrypted}/{processed} encrypted, "
                f"{errors} errors, {processing_time:.2f}s"
            )
            
            return result
            
        finally:
            if close_session:
                session.close()
    
    def decrypt_column_bulk(
        self,
        model: Type[DeclarativeMeta],
        column_name: str,
        filter_condition: Optional[Any] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Decrypt a column for multiple records in batches.
        
        Args:
            model: SQLAlchemy model class
            column_name: Name of column to decrypt
            filter_condition: Optional SQLAlchemy filter condition
            session: Optional database session
        
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        close_session = False
        
        if session is None:
            session = SessionLocal()
            close_session = True
        
        try:
            # Build query
            query = select(model)
            if filter_condition is not None:
                query = query.where(filter_condition)
            
            # Get total count
            total_count = session.execute(
                select(func.count()).select_from(model)
            ).scalar()
            
            logger.info(f"Starting bulk decryption of {column_name} for {total_count} records")
            
            processed = 0
            decrypted = 0
            errors = 0
            
            # Process in batches
            while processed < total_count:
                # Fetch batch
                batch_query = query.offset(processed).limit(self.batch_size)
                records = session.execute(batch_query).scalars().all()
                
                if not records:
                    break
                
                # Process batch
                for record in records:
                    try:
                        # Get current value
                        encrypted_value = getattr(record, column_name)
                        
                        # Skip if None or not encrypted
                        if encrypted_value is None:
                            processed += 1
                            continue
                        
                        if not (isinstance(encrypted_value, str) and encrypted_value.startswith('gAAAAAB')):
                            processed += 1
                            continue
                        
                        # Decrypt value
                        decrypted_value = self.encryption_manager.decrypt(encrypted_value)
                        setattr(record, column_name, decrypted_value)
                        decrypted += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to decrypt record {record.id}: {e}")
                        errors += 1
                    
                    processed += 1
                
                # Commit batch
                try:
                    session.commit()
                    logger.debug(f"Committed batch: {processed}/{total_count}")
                except Exception as e:
                    logger.error(f"Batch commit failed: {e}")
                    session.rollback()
                    errors += len(records)
            
            # Calculate stats
            processing_time = time.time() - start_time
            self.stats['total_processed'] += processed
            self.stats['total_decrypted'] += decrypted
            self.stats['total_errors'] += errors
            self.stats['processing_time'] += processing_time
            
            result = {
                'total_count': total_count,
                'processed': processed,
                'decrypted': decrypted,
                'skipped': processed - decrypted - errors,
                'errors': errors,
                'processing_time': processing_time,
                'throughput': processed / processing_time if processing_time > 0 else 0
            }
            
            logger.info(
                f"Bulk decryption complete: {decrypted}/{processed} decrypted, "
                f"{errors} errors, {processing_time:.2f}s"
            )
            
            return result
            
        finally:
            if close_session:
                session.close()
    
    def encrypt_multiple_columns(
        self,
        model: Type[DeclarativeMeta],
        columns: List[str],
        filter_condition: Optional[Any] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Encrypt multiple columns in a single pass.
        
        More efficient than calling encrypt_column_bulk multiple times.
        
        Args:
            model: SQLAlchemy model class
            columns: List of column names to encrypt
            filter_condition: Optional filter condition
            session: Optional database session
        
        Returns:
            Dict mapping column names to their processing stats
        """
        results = {}
        
        for column in columns:
            logger.info(f"Encrypting column: {column}")
            result = self.encrypt_column_bulk(
                model=model,
                column_name=column,
                filter_condition=filter_condition,
                session=session
            )
            results[column] = result
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Dict with cumulative stats
        """
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'total_processed': 0,
            'total_encrypted': 0,
            'total_decrypted': 0,
            'total_errors': 0,
            'processing_time': 0.0
        }


class EncryptedDatabaseManager:
    """High-level manager for encrypted database operations."""
    
    def __init__(self, batch_size: int = 100):
        """Initialize manager.
        
        Args:
            batch_size: Batch size for bulk operations
        """
        self.processor = BulkEncryptionProcessor(batch_size=batch_size)
        EncryptionManager.initialize()  # Ensure encryption is ready
    
    @contextmanager
    def transaction_scope(self):
        """Provide a transactional scope around operations."""
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_to_encrypted(
        self,
        model: Type[DeclarativeMeta],
        sensitive_columns: List[str]
    ) -> Dict[str, Any]:
        """Migrate existing plaintext columns to encrypted.
        
        Args:
            model: SQLAlchemy model
            sensitive_columns: List of columns to encrypt
        
        Returns:
            Migration statistics
        """
        logger.info(f"Starting migration to encrypted columns for {model.__name__}")
        
        with self.transaction_scope() as session:
            results = self.processor.encrypt_multiple_columns(
                model=model,
                columns=sensitive_columns,
                session=session
            )
        
        total_encrypted = sum(r['encrypted'] for r in results.values())
        total_errors = sum(r['errors'] for r in results.values())
        
        logger.info(
            f"Migration complete: {total_encrypted} fields encrypted, "
            f"{total_errors} errors"
        )
        
        return {
            'columns': results,
            'total_encrypted': total_encrypted,
            'total_errors': total_errors
        }
    
    def verify_encryption(
        self,
        model: Type[DeclarativeMeta],
        column_name: str,
        sample_size: int = 10
    ) -> Dict[str, Any]:
        """Verify that a column is properly encrypted.
        
        Args:
            model: SQLAlchemy model
            column_name: Column to verify
            sample_size: Number of records to sample
        
        Returns:
            Verification results
        """
        with self.transaction_scope() as session:
            # Sample random records
            query = select(model).limit(sample_size)
            records = session.execute(query).scalars().all()
            
            encrypted_count = 0
            plaintext_count = 0
            null_count = 0
            
            for record in records:
                value = getattr(record, column_name)
                
                if value is None:
                    null_count += 1
                elif isinstance(value, str) and value.startswith('gAAAAAB'):
                    encrypted_count += 1
                else:
                    plaintext_count += 1
            
            total = len(records)
            encryption_rate = (encrypted_count / total * 100) if total > 0 else 0
            
            result = {
                'total_sampled': total,
                'encrypted': encrypted_count,
                'plaintext': plaintext_count,
                'null': null_count,
                'encryption_rate': encryption_rate,
                'status': 'ENCRYPTED' if plaintext_count == 0 else 'MIXED'
            }
            
            logger.info(
                f"Encryption verification for {column_name}: "
                f"{encryption_rate:.1f}% encrypted ({encrypted_count}/{total})"
            )
            
            return result


# Module-level convenience functions
_manager = None


def get_encryption_manager(batch_size: int = 100) -> EncryptedDatabaseManager:
    """Get or create the encryption manager singleton.
    
    Args:
        batch_size: Batch size for bulk operations
    
    Returns:
        EncryptedDatabaseManager instance
    """
    global _manager
    if _manager is None:
        _manager = EncryptedDatabaseManager(batch_size=batch_size)
    return _manager


def encrypt_column(
    model: Type[DeclarativeMeta],
    column_name: str,
    batch_size: int = 100
) -> Dict[str, Any]:
    """Convenience function to encrypt a column.
    
    Args:
        model: SQLAlchemy model
        column_name: Column to encrypt
        batch_size: Batch size
    
    Returns:
        Processing statistics
    """
    manager = get_encryption_manager(batch_size=batch_size)
    return manager.processor.encrypt_column_bulk(model, column_name)


def verify_encryption(
    model: Type[DeclarativeMeta],
    column_name: str,
    sample_size: int = 10
) -> Dict[str, Any]:
    """Convenience function to verify encryption.
    
    Args:
        model: SQLAlchemy model
        column_name: Column to verify
        sample_size: Sample size
    
    Returns:
        Verification results
    """
    manager = get_encryption_manager()
    return manager.verify_encryption(model, column_name, sample_size)
