"""Unit Tests for Encrypted Database Layer.

Tests bulk encryption/decryption operations with various scenarios:
- Single column encryption
- Multiple column encryption
- Batch processing
- Error handling
- Performance verification

Author: v0-strategy-engine-pro
Version: 1.0
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database.encrypted_db import (
    BulkEncryptionProcessor,
    EncryptedDatabaseManager,
    get_encryption_manager,
    encrypt_column,
    verify_encryption
)
from database.encrypted_fields import EncryptionManager, EncryptedString


# Test database setup
Base = declarative_base()


class TestUser(Base):
    """Test model for encryption tests."""
    __tablename__ = 'test_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    api_key = Column(String(500))  # Will be encrypted
    secret_key = Column(String(500))  # Will be encrypted
    email = Column(String(200))


@pytest.fixture(scope='function')
def test_db():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize encryption
    EncryptionManager.initialize()
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture(scope='function')
def sample_users(test_db):
    """Create sample users for testing."""
    users = [
        TestUser(
            id=i,
            username=f'user_{i}',
            api_key=f'api_key_{i}',
            secret_key=f'secret_key_{i}',
            email=f'user_{i}@example.com'
        )
        for i in range(1, 11)
    ]
    
    test_db.add_all(users)
    test_db.commit()
    
    return users


class TestBulkEncryptionProcessor:
    """Test suite for BulkEncryptionProcessor."""
    
    def test_initialization(self):
        """Test processor initialization."""
        processor = BulkEncryptionProcessor(batch_size=50)
        assert processor.batch_size == 50
        assert processor.stats['total_processed'] == 0
    
    def test_encrypt_column_bulk(self, test_db, sample_users):
        """Test bulk column encryption."""
        processor = BulkEncryptionProcessor(batch_size=5)
        
        # Encrypt api_key column
        result = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Verify results
        assert result['total_count'] == 10
        assert result['encrypted'] == 10
        assert result['errors'] == 0
        assert result['processing_time'] > 0
        
        # Verify data is encrypted
        users = test_db.query(TestUser).all()
        for user in users:
            assert user.api_key.startswith('gAAAAAB')  # Fernet token prefix
    
    def test_decrypt_column_bulk(self, test_db, sample_users):
        """Test bulk column decryption."""
        processor = BulkEncryptionProcessor(batch_size=5)
        
        # First encrypt
        processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Then decrypt
        result = processor.decrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Verify results
        assert result['decrypted'] == 10
        assert result['errors'] == 0
        
        # Verify data is decrypted
        users = test_db.query(TestUser).all()
        for i, user in enumerate(users, 1):
            assert user.api_key == f'api_key_{i}'
    
    def test_encrypt_multiple_columns(self, test_db, sample_users):
        """Test encrypting multiple columns."""
        processor = BulkEncryptionProcessor(batch_size=5)
        
        results = processor.encrypt_multiple_columns(
            model=TestUser,
            columns=['api_key', 'secret_key'],
            session=test_db
        )
        
        # Verify both columns encrypted
        assert 'api_key' in results
        assert 'secret_key' in results
        assert results['api_key']['encrypted'] == 10
        assert results['secret_key']['encrypted'] == 10
        
        # Verify data
        users = test_db.query(TestUser).all()
        for user in users:
            assert user.api_key.startswith('gAAAAAB')
            assert user.secret_key.startswith('gAAAAAB')
    
    def test_skip_already_encrypted(self, test_db, sample_users):
        """Test that already encrypted data is skipped."""
        processor = BulkEncryptionProcessor(batch_size=5)
        
        # Encrypt once
        result1 = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        assert result1['encrypted'] == 10
        
        # Try to encrypt again
        result2 = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        assert result2['encrypted'] == 0  # Should skip all
        assert result2['skipped'] == 10
    
    def test_skip_null_values(self, test_db):
        """Test that null values are handled properly."""
        # Create users with null api_key
        users = [
            TestUser(id=i, username=f'user_{i}', api_key=None)
            for i in range(1, 6)
        ]
        test_db.add_all(users)
        test_db.commit()
        
        processor = BulkEncryptionProcessor(batch_size=5)
        result = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        assert result['encrypted'] == 0
        assert result['skipped'] == 5
    
    def test_batch_processing(self, test_db, sample_users):
        """Test that batching works correctly."""
        # Use small batch size
        processor = BulkEncryptionProcessor(batch_size=3)
        
        result = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Should process all records despite small batch size
        assert result['encrypted'] == 10
        assert result['processed'] == 10
    
    def test_get_stats(self):
        """Test statistics tracking."""
        processor = BulkEncryptionProcessor()
        
        initial_stats = processor.get_stats()
        assert initial_stats['total_processed'] == 0
        assert initial_stats['total_encrypted'] == 0
        
        # Stats should be independent copy
        initial_stats['total_processed'] = 100
        assert processor.stats['total_processed'] == 0
    
    def test_reset_stats(self):
        """Test statistics reset."""
        processor = BulkEncryptionProcessor()
        processor.stats['total_processed'] = 100
        processor.stats['total_encrypted'] = 50
        
        processor.reset_stats()
        
        assert processor.stats['total_processed'] == 0
        assert processor.stats['total_encrypted'] == 0


class TestEncryptedDatabaseManager:
    """Test suite for EncryptedDatabaseManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = EncryptedDatabaseManager(batch_size=50)
        assert manager.processor.batch_size == 50
    
    def test_migrate_to_encrypted(self, test_db, sample_users):
        """Test migration of plaintext to encrypted."""
        manager = EncryptedDatabaseManager(batch_size=5)
        
        # Temporarily patch SessionLocal to use test_db
        with patch('database.encrypted_db.SessionLocal', return_value=test_db):
            result = manager.migrate_to_encrypted(
                model=TestUser,
                sensitive_columns=['api_key', 'secret_key']
            )
        
        # Verify migration
        assert result['total_encrypted'] == 20  # 10 users * 2 columns
        assert 'api_key' in result['columns']
        assert 'secret_key' in result['columns']
    
    def test_verify_encryption_all_encrypted(self, test_db, sample_users):
        """Test verification when all records are encrypted."""
        # Encrypt first
        processor = BulkEncryptionProcessor()
        processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        manager = EncryptedDatabaseManager()
        
        with patch('database.encrypted_db.SessionLocal', return_value=test_db):
            result = manager.verify_encryption(
                model=TestUser,
                column_name='api_key',
                sample_size=10
            )
        
        assert result['status'] == 'ENCRYPTED'
        assert result['encryption_rate'] == 100.0
        assert result['plaintext'] == 0
    
    def test_verify_encryption_mixed(self, test_db):
        """Test verification with mixed encrypted/plaintext."""
        # Create users with mixed encryption
        encrypted_manager = EncryptionManager()
        users = []
        
        for i in range(1, 6):
            # First 3 encrypted, last 2 plaintext
            api_key = encrypted_manager.encrypt(f'api_key_{i}') if i <= 3 else f'api_key_{i}'
            users.append(
                TestUser(id=i, username=f'user_{i}', api_key=api_key)
            )
        
        test_db.add_all(users)
        test_db.commit()
        
        manager = EncryptedDatabaseManager()
        
        with patch('database.encrypted_db.SessionLocal', return_value=test_db):
            result = manager.verify_encryption(
                model=TestUser,
                column_name='api_key',
                sample_size=5
            )
        
        assert result['status'] == 'MIXED'
        assert result['encrypted'] == 3
        assert result['plaintext'] == 2
        assert result['encryption_rate'] == 60.0


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_get_encryption_manager(self):
        """Test singleton manager creation."""
        manager1 = get_encryption_manager()
        manager2 = get_encryption_manager()
        
        # Should be same instance
        assert manager1 is manager2
    
    @patch('database.encrypted_db.get_encryption_manager')
    def test_encrypt_column_convenience(self, mock_manager):
        """Test encrypt_column convenience function."""
        mock_processor = Mock()
        mock_processor.encrypt_column_bulk.return_value = {'encrypted': 10}
        mock_manager.return_value.processor = mock_processor
        
        result = encrypt_column(
            model=TestUser,
            column_name='api_key',
            batch_size=50
        )
        
        assert result['encrypted'] == 10
        mock_processor.encrypt_column_bulk.assert_called_once()
    
    @patch('database.encrypted_db.get_encryption_manager')
    def test_verify_encryption_convenience(self, mock_manager):
        """Test verify_encryption convenience function."""
        mock_instance = Mock()
        mock_instance.verify_encryption.return_value = {
            'status': 'ENCRYPTED',
            'encryption_rate': 100.0
        }
        mock_manager.return_value = mock_instance
        
        result = verify_encryption(
            model=TestUser,
            column_name='api_key',
            sample_size=10
        )
        
        assert result['status'] == 'ENCRYPTED'
        assert result['encryption_rate'] == 100.0


class TestPerformance:
    """Performance tests for encryption operations."""
    
    def test_bulk_encryption_performance(self, test_db):
        """Test that bulk encryption is reasonably fast."""
        # Create 100 users
        users = [
            TestUser(
                id=i,
                username=f'user_{i}',
                api_key=f'api_key_{i}'
            )
            for i in range(1, 101)
        ]
        test_db.add_all(users)
        test_db.commit()
        
        processor = BulkEncryptionProcessor(batch_size=20)
        result = processor.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Should encrypt 100 records in under 5 seconds
        assert result['processing_time'] < 5.0
        assert result['throughput'] > 10  # At least 10 records/sec
    
    def test_batch_size_effect(self, test_db, sample_users):
        """Test that larger batch sizes improve throughput."""
        # Small batch
        processor_small = BulkEncryptionProcessor(batch_size=2)
        result_small = processor_small.encrypt_column_bulk(
            model=TestUser,
            column_name='api_key',
            session=test_db
        )
        
        # Reset data
        test_db.rollback()
        
        # Large batch
        processor_large = BulkEncryptionProcessor(batch_size=10)
        result_large = processor_large.encrypt_column_bulk(
            model=TestUser,
            column_name='secret_key',
            session=test_db
        )
        
        # Larger batch should be faster (or at least not significantly slower)
        # Allow some variance in timing
        assert result_large['throughput'] >= result_small['throughput'] * 0.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
