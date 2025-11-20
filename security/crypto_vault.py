"""Cryptographic Vault - Phase 2

Military-grade encryption for API keys and sensitive credentials.
Uses AES-256-GCM for symmetric encryption and Argon2 for password hashing.
"""

import os
import logging
from typing import Optional, Tuple
import base64
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2
from cryptography.hazmat.backends import default_backend
import secrets


logger = logging.getLogger(__name__)


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "AES-256-GCM"
    AES_128_GCM = "AES-128-GCM"


class KeyDerivationMethod(str, Enum):
    """Key derivation methods."""
    ARGON2 = "ARGON2"
    PBKDF2 = "PBKDF2"


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes  # IV/nonce for GCM
    tag: bytes   # Authentication tag for GCM
    algorithm: str = "AES-256-GCM"
    salt: Optional[bytes] = None  # For key derivation
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class CryptoVault:
    """Military-grade cryptographic vault for credential management.
    
    Features:
    - AES-256-GCM encryption (authenticated encryption)
    - Argon2 key derivation (memory-hard, GPU-resistant)
    - Secure random nonce generation
    - Authentication tag verification
    - No credentials logged or exposed
    """
    
    def __init__(
        self,
        master_key: Optional[bytes] = None,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    ):
        """Initialize crypto vault.
        
        Args:
            master_key: Optional pre-generated master key (32 bytes for AES-256)
            algorithm: Encryption algorithm to use
        """
        self.algorithm = algorithm
        self.master_key = master_key or self._generate_master_key()
        self._validate_key_size()
    
    @staticmethod
    def _generate_master_key(key_size: int = 32) -> bytes:
        """Generate cryptographically secure master key.
        
        Args:
            key_size: Key size in bytes (32 for AES-256, 16 for AES-128)
            
        Returns:
            Random key bytes
        """
        return secrets.token_bytes(key_size)
    
    def _validate_key_size(self) -> None:
        """Validate master key size matches algorithm."""
        if self.algorithm == EncryptionAlgorithm.AES_256_GCM:
            if len(self.master_key) != 32:
                raise ValueError("AES-256 requires 32-byte key")
        elif self.algorithm == EncryptionAlgorithm.AES_128_GCM:
            if len(self.master_key) != 16:
                raise ValueError("AES-128 requires 16-byte key")
    
    def encrypt(self, plaintext: str, associated_data: Optional[str] = None) -> EncryptedData:
        """Encrypt plaintext with AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional authenticated data (not encrypted but authenticated)
            
        Returns:
            EncryptedData with ciphertext, nonce, and tag
        """
        # Generate random 96-bit nonce (recommended for GCM)
        nonce = secrets.token_bytes(12)
        
        # Initialize cipher
        cipher = AESGCM(self.master_key)
        
        # Encode plaintext and prepare associated data
        plaintext_bytes = plaintext.encode('utf-8')
        aad = associated_data.encode('utf-8') if associated_data else None
        
        try:
            # Encrypt with GCM (produces ciphertext + authentication tag)
            ciphertext = cipher.encrypt(nonce, plaintext_bytes, aad)
            
            # GCM appends 16-byte tag to ciphertext, extract it
            tag = ciphertext[-16:]
            actual_ciphertext = ciphertext[:-16]
            
            logger.debug("Encryption successful (AES-256-GCM)")
            
            return EncryptedData(
                ciphertext=actual_ciphertext,
                nonce=nonce,
                tag=tag,
                algorithm=self.algorithm.value
            )
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(
        self,
        encrypted_data: EncryptedData,
        associated_data: Optional[str] = None
    ) -> str:
        """Decrypt AES-256-GCM encrypted data.
        
        Args:
            encrypted_data: EncryptedData object
            associated_data: Optional authenticated data (must match encryption)
            
        Returns:
            Decrypted plaintext
            
        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        try:
            cipher = AESGCM(self.master_key)
            
            # Reconstruct ciphertext + tag for decryption
            ciphertext_with_tag = encrypted_data.ciphertext + encrypted_data.tag
            
            # Prepare associated data
            aad = associated_data.encode('utf-8') if associated_data else None
            
            # Decrypt with authentication tag verification
            plaintext_bytes = cipher.decrypt(
                encrypted_data.nonce,
                ciphertext_with_tag,
                aad
            )
            
            logger.debug("Decryption successful (AES-256-GCM)")
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_key(self, key: str, key_type: str) -> str:
        """Encrypt API key or secret.
        
        Args:
            key: API key/secret to encrypt
            key_type: Type of key (e.g., 'binance_api', 'oanda_secret')
            
        Returns:
            Base64-encoded encrypted key for storage
        """
        encrypted = self.encrypt(key, associated_data=key_type)
        
        # Encode for storage/transmission
        storage_format = {
            'ciphertext': base64.b64encode(encrypted.ciphertext).decode(),
            'nonce': base64.b64encode(encrypted.nonce).decode(),
            'tag': base64.b64encode(encrypted.tag).decode(),
            'algorithm': encrypted.algorithm
        }
        
        import json
        return base64.b64encode(json.dumps(storage_format).encode()).decode()
    
    def decrypt_key(self, encrypted_key: str, key_type: str) -> str:
        """Decrypt stored API key.
        
        Args:
            encrypted_key: Base64-encoded encrypted key
            key_type: Type of key (must match encryption)
            
        Returns:
            Decrypted API key/secret
        """
        import json
        
        # Decode from storage format
        storage_format = json.loads(
            base64.b64decode(encrypted_key.encode()).decode()
        )
        
        encrypted_data = EncryptedData(
            ciphertext=base64.b64decode(storage_format['ciphertext']),
            nonce=base64.b64decode(storage_format['nonce']),
            tag=base64.b64decode(storage_format['tag']),
            algorithm=storage_format['algorithm']
        )
        
        return self.decrypt(encrypted_data, associated_data=key_type)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """Hash password with Argon2 (memory-hard, GPU-resistant).
        
        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_password_base64, salt_base64)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # Argon2 parameters for maximum security
        kdf = Argon2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=3,
            lanes=4,
            memory_cost=65540,  # 64 MB (high memory cost)
            backend=default_backend()
        )
        
        hash_bytes = kdf.derive(password.encode())
        
        return (
            base64.b64encode(hash_bytes).decode(),
            base64.b64encode(salt).decode()
        )
    
    @staticmethod
    def verify_password(password: str, hash_base64: str, salt_base64: str) -> bool:
        """Verify password against Argon2 hash.
        
        Args:
            password: Password to verify
            hash_base64: Base64-encoded hash
            salt_base64: Base64-encoded salt
            
        Returns:
            True if password matches hash
        """
        import hmac
        
        try:
            salt = base64.b64decode(salt_base64.encode())
            
            kdf = Argon2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=3,
                lanes=4,
                memory_cost=65540,
                backend=default_backend()
            )
            
            computed_hash = kdf.derive(password.encode())
            stored_hash = base64.b64decode(hash_base64.encode())
            
            # Use timing-safe comparison
            return hmac.compare_digest(computed_hash, stored_hash)
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def export_master_key(self) -> str:
        """Export master key for backup (handle with extreme care).
        
        Returns:
            Base64-encoded master key
        """
        logger.warning("Master key exported - store securely!")
        return base64.b64encode(self.master_key).decode()
    
    @classmethod
    def import_master_key(cls, key_base64: str) -> 'CryptoVault':
        """Import master key from backup.
        
        Args:
            key_base64: Base64-encoded master key
            
        Returns:
            CryptoVault instance with imported key
        """
        master_key = base64.b64decode(key_base64.encode())
        logger.warning("Master key imported")
        return cls(master_key=master_key)
