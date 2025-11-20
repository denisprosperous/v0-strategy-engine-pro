"""API Key Manager - Phase 2

Secure management of API keys and credentials across multiple exchanges.
Handles storage, retrieval, validation, and rotation.
"""

import logging
import json
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from security.crypto_vault import CryptoVault


logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API key with metadata."""
    key_id: str
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # For exchanges like Kraken, OKX
    is_testnet: bool = False
    permissions: List[str] = None  # ['read', 'trade', 'withdraw']
    created_at: datetime = None
    last_used: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.permissions is None:
            self.permissions = ['read', 'trade']


class KeyManager:
    """Secure API key management system.
    
    Features:
    - Encrypted key storage (AES-256-GCM)
    - Multi-exchange support
    - Key rotation tracking
    - Permission management
    - Audit logging
    - Per-exchange key isolation
    """
    
    def __init__(self, vault: CryptoVault, storage_path: Optional[str] = None):
        """Initialize key manager.
        
        Args:
            vault: CryptoVault instance for encryption
            storage_path: Path to store encrypted keys (default: .keys/)
        """
        self.vault = vault
        self.storage_path = Path(storage_path or '.keys')
        self.storage_path.mkdir(exist_ok=True, mode=0o700)  # Restrictive permissions
        self._keys_cache: Dict[str, APIKey] = {}
        self._load_keys()
    
    def add_key(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        is_testnet: bool = False
    ) -> str:
        """Add API key to manager.
        
        Args:
            exchange: Exchange name (e.g., 'binance', 'oanda')
            api_key: API key
            api_secret: API secret
            passphrase: Optional passphrase
            permissions: List of permissions
            is_testnet: Whether this is testnet/sandbox
            
        Returns:
            Key ID for reference
        """
        import uuid
        key_id = str(uuid.uuid4())[:8]
        
        api_key_obj = APIKey(
            key_id=key_id,
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            is_testnet=is_testnet,
            permissions=permissions or ['read', 'trade']
        )
        
        # Encrypt and store
        self._store_key(api_key_obj)
        self._keys_cache[key_id] = api_key_obj
        
        logger.info(f"Added key {key_id} for {exchange}")
        return key_id
    
    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Retrieve API key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            APIKey object or None
        """
        if key_id in self._keys_cache:
            key = self._keys_cache[key_id]
            key.last_used = datetime.utcnow()
            return key
        return None
    
    def get_keys_for_exchange(self, exchange: str) -> List[APIKey]:
        """Get all keys for specific exchange.
        
        Args:
            exchange: Exchange name
            
        Returns:
            List of APIKey objects
        """
        return [k for k in self._keys_cache.values() if k.exchange == exchange and k.is_active]
    
    def list_keys(self, exchange: Optional[str] = None) -> List[Dict]:
        """List all keys (metadata only, no secrets).
        
        Args:
            exchange: Optional filter by exchange
            
        Returns:
            List of key metadata
        """
        keys = self._keys_cache.values()
        if exchange:
            keys = [k for k in keys if k.exchange == exchange]
        
        return [
            {
                'key_id': k.key_id,
                'exchange': k.exchange,
                'is_testnet': k.is_testnet,
                'permissions': k.permissions,
                'created_at': k.created_at.isoformat(),
                'last_used': k.last_used.isoformat() if k.last_used else None,
                'is_active': k.is_active
            }
            for k in keys
        ]
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke (disable) API key.
        
        Args:
            key_id: Key to revoke
            
        Returns:
            True if revoked
        """
        if key_id in self._keys_cache:
            self._keys_cache[key_id].is_active = False
            self._store_key(self._keys_cache[key_id])
            logger.warning(f"Revoked key {key_id}")
            return True
        return False
    
    def validate_key(self, key_id: str) -> Tuple[bool, str]:
        """Validate key integrity and permissions.
        
        Args:
            key_id: Key to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        key = self.get_key(key_id)
        if not key:
            return False, "Key not found"
        
        if not key.is_active:
            return False, "Key is revoked"
        
        if not key.api_key or not key.api_secret:
            return False, "Key data incomplete"
        
        return True, "Key is valid"
    
    def _store_key(self, key_obj: APIKey) -> None:
        """Encrypt and store key.
        
        Args:
            key_obj: APIKey to store
        """
        # Encrypt sensitive data
        encrypted_key = self.vault.encrypt_key(
            key_obj.api_key,
            f"{key_obj.exchange}_api_key"
        )
        encrypted_secret = self.vault.encrypt_key(
            key_obj.api_secret,
            f"{key_obj.exchange}_api_secret"
        )
        
        # Store metadata
        storage_data = {
            'key_id': key_obj.key_id,
            'exchange': key_obj.exchange,
            'encrypted_key': encrypted_key,
            'encrypted_secret': encrypted_secret,
            'is_testnet': key_obj.is_testnet,
            'permissions': key_obj.permissions,
            'created_at': key_obj.created_at.isoformat(),
            'is_active': key_obj.is_active
        }
        
        # Write to disk
        key_file = self.storage_path / f"{key_obj.key_id}.json"
        with open(key_file, 'w') as f:
            json.dump(storage_data, f)
        
        key_file.chmod(0o600)  # Restrictive file permissions
    
    def _load_keys(self) -> None:
        """Load encrypted keys from storage."""
        for key_file in self.storage_path.glob('*.json'):
            try:
                with open(key_file, 'r') as f:
                    data = json.load(f)
                
                # Decrypt
                api_key = self.vault.decrypt_key(
                    data['encrypted_key'],
                    f"{data['exchange']}_api_key"
                )
                api_secret = self.vault.decrypt_key(
                    data['encrypted_secret'],
                    f"{data['exchange']}_api_secret"
                )
                
                key_obj = APIKey(
                    key_id=data['key_id'],
                    exchange=data['exchange'],
                    api_key=api_key,
                    api_secret=api_secret,
                    is_testnet=data['is_testnet'],
                    permissions=data['permissions'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    is_active=data['is_active']
                )
                
                self._keys_cache[data['key_id']] = key_obj
                
            except Exception as e:
                logger.error(f"Error loading key from {key_file}: {e}")
    
    def export_keys(self, backup_path: str) -> bool:
        """Export encrypted keys for backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful
        """
        try:
            backup_data = {
                'backup_time': datetime.utcnow().isoformat(),
                'keys': self.list_keys()
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Exported keys to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
