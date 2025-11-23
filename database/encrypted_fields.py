"""Encrypted Fields Module - Phase 2.1

Provides field-level encryption for sensitive data in the database.
Supports encryption/decryption of strings, JSON, and binary data.
Uses Fernet (symmetric encryption) from the cryptography library.
"""

import os
import json
import logging
from typing import Any, Optional, Type, TypeVar
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, String, CHAR
from sqlalchemy.ext.hybrid import hybrid_property

logger = logging.getLogger(__name__)
T = TypeVar('T')


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    _instance = None
    _cipher = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, key: Optional[str] = None):
        """Initialize encryption with a key.
        
        Args:
            key: Encryption key (base64 encoded). If None, loads from env var.
        """
        if key is None:
            key = os.getenv('ENCRYPTION_KEY')
            if not key:
                logger.warning("ENCRYPTION_KEY not found, generating new key")
                key = Fernet.generate_key().decode()
                os.environ['ENCRYPTION_KEY'] = key
        
        try:
            # Ensure key is bytes
            if isinstance(key, str):
                key = key.encode()
            cls._cipher = Fernet(key)
            logger.info("Encryption manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    @classmethod
    def generate_key(cls) -> str:
        """Generate a new encryption key.
        
        Returns:
            Base64 encoded key
        """
        return Fernet.generate_key().decode()
    
    @classmethod
    def encrypt(cls, data: Any) -> str:
        """Encrypt data.
        
        Args:
            data: Data to encrypt (string, dict, or bytes)
        
        Returns:
            Encrypted string (base64 encoded)
        """
        if cls._cipher is None:
            cls.initialize()
        
        try:
            # Convert data to JSON string if dict
            if isinstance(data, dict):
                data = json.dumps(data)
            # Convert to bytes
            if isinstance(data, str):
                data = data.encode()
            
            encrypted = cls._cipher.encrypt(data)
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")
    
    @classmethod
    def decrypt(cls, encrypted_data: str, as_json: bool = False) -> Any:
        """Decrypt data.
        
        Args:
            encrypted_data: Encrypted string to decrypt
            as_json: If True, attempt to parse result as JSON
        
        Returns:
            Decrypted data (string, dict, or bytes)
        """
        if cls._cipher is None:
            cls.initialize()
        
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode()
            
            decrypted = cls._cipher.decrypt(encrypted_data)
            result = decrypted.decode()
            
            if as_json:
                result = json.loads(result)
            
            return result
        except InvalidToken:
            logger.error("Invalid encryption token - possible key mismatch")
            raise ValueError("Failed to decrypt data - invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")


class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted string columns."""
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        """Encrypt before storing in database."""
        if value is None:
            return None
        try:
            return EncryptionManager.encrypt(value)
        except Exception as e:
            logger.error(f"Failed to encrypt field: {e}")
            return value  # Fall back to unencrypted
    
    def process_result_value(self, value: Any, dialect: Any) -> Optional[str]:
        """Decrypt after retrieving from database."""
        if value is None:
            return None
        try:
            return EncryptionManager.decrypt(value)
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            return value  # Fall back to encrypted value


class EncryptedJSON(TypeDecorator):
    """SQLAlchemy type for encrypted JSON columns."""
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        """Encrypt JSON before storing."""
        if value is None:
            return None
        try:
            return EncryptionManager.encrypt(value)
        except Exception as e:
            logger.error(f"Failed to encrypt JSON field: {e}")
            return value
    
    def process_result_value(self, value: Any, dialect: Any) -> Optional[dict]:
        """Decrypt JSON after retrieval."""
        if value is None:
            return None
        try:
            return EncryptionManager.decrypt(value, as_json=True)
        except Exception as e:
            logger.error(f"Failed to decrypt JSON field: {e}")
            return {}


class EncryptionHelper:
    """Helper utility class for encryption operations."""
    
    @staticmethod
    def is_encrypted(value: str) -> bool:
        """Check if a value appears to be encrypted.
        
        Args:
            value: Value to check
        
        Returns:
            True if value looks like encrypted data
        """
        try:
            if not isinstance(value, str):
                return False
            # Fernet tokens are prefixed with 'gAAAAAB'
            return value.startswith('gAAAAAB')
        except Exception:
            return False
    
    @staticmethod
    def rotate_key(old_data: list, new_key: str) -> list:
        """Rotate encryption key for existing encrypted data.
        
        Args:
            old_data: List of encrypted values
            new_key: New encryption key
        
        Returns:
            List of data re-encrypted with new key
        """
        current_manager = EncryptionManager()
        rotated_data = []
        
        try:
            for encrypted_value in old_data:
                # Decrypt with old key
                decrypted = current_manager.decrypt(encrypted_value)
                # Encrypt with new key
                EncryptionManager.initialize(new_key)
                reencrypted = EncryptionManager.encrypt(decrypted)
                rotated_data.append(reencrypted)
            
            logger.info(f"Successfully rotated {len(rotated_data)} encrypted values")
            return rotated_data
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise
