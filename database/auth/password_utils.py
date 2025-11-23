"""
Password Utilities - Phase 2.3b

Provides secure password hashing and verification using bcrypt.
Supports password strength validation and migration from legacy formats.

Author: Development Team
Date: 2024
Version: 2.3.0
"""

import logging
import re
from typing import Optional, Dict, Any

try:
    import bcrypt
except ImportError:
    raise ImportError("bcrypt library required: pip install bcrypt")

logger = logging.getLogger(__name__)


class PasswordValidator:
    """
    Validates password strength and compliance with security policies.
    
    Requirements:
    - Minimum 12 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    
    MIN_LENGTH = 12
    SPECIAL_CHARS = r"[!@#$%^&*(),.?\":{}|<>]"
    
    @staticmethod
    def validate_password(
        password: str,
        min_length: int = MIN_LENGTH,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True
    ) -> Dict[str, Any]:
        """
        Validate password against security requirements.
        
        Args:
            password: Password to validate
            min_length: Minimum password length
            require_uppercase: Require uppercase letter
            require_lowercase: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
        
        Returns:
            Dictionary with validation results and feedback
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "strength": "weak"
        }
        
        if not password:
            result["valid"] = False
            result["errors"].append("Password cannot be empty")
            return result
        
        # Check length
        if len(password) < min_length:
            result["valid"] = False
            result["errors"].append(
                f"Password must be at least {min_length} characters long"
            )
        elif len(password) >= 20:
            result["strength"] = "strong"
        
        # Check uppercase
        if require_uppercase and not re.search(r"[A-Z]", password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one uppercase letter")
        
        # Check lowercase
        if require_lowercase and not re.search(r"[a-z]", password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one lowercase letter")
        
        # Check digit
        if require_digit and not re.search(r"\d", password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one digit")
        
        # Check special character
        if require_special and not re.search(PasswordValidator.SPECIAL_CHARS, password):
            result["valid"] = False
            result["errors"].append(
                "Password must contain at least one special character (!@#$%^&*)"
            )
        
        # Determine strength
        if result["valid"]:
            if len(password) >= 16:
                result["strength"] = "very_strong"
            elif len(password) >= 14:
                result["strength"] = "strong"
            else:
                result["strength"] = "medium"
        
        return result
    
    @staticmethod
    def is_common_password(password: str) -> bool:
        """
        Check if password is in common password list (simplified).
        
        Args:
            password: Password to check
        
        Returns:
            True if password is common
        """
        common_passwords = {
            "password123", "admin123", "trading123", "binance123",
            "crypto123", "bitcoin123", "ethereum123", "qwerty123",
            "letmein123", "welcome123"
        }
        
        return password.lower() in common_passwords


class PasswordHasher:
    """
    Handles secure password hashing and verification using bcrypt.
    """
    
    # Bcrypt cost factor (higher = slower but more secure)
    # 12 provides good balance between security and performance
    ROUNDS = 12
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Password to hash
        
        Returns:
            Hashed password (bcrypt format)
        
        Raises:
            ValueError: If password validation fails
        """
        # Validate password before hashing
        validation = PasswordValidator.validate_password(password)
        if not validation["valid"]:
            errors = "; ".join(validation["errors"])
            raise ValueError(f"Invalid password: {errors}")
        
        if PasswordValidator.is_common_password(password):
            raise ValueError("Password is too common. Please choose a stronger password.")
        
        try:
            salt = bcrypt.gensalt(rounds=PasswordHasher.ROUNDS)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            logger.debug("Password hashed successfully")
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Bcrypt hash
        
        Returns:
            True if password matches hash
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    @staticmethod
    def needs_rehash(hashed_password: str, rounds: int = ROUNDS) -> bool:
        """
        Check if password hash needs rehashing (e.g., cost factor outdated).
        
        Args:
            hashed_password: Existing bcrypt hash
            rounds: Expected bcrypt rounds
        
        Returns:
            True if password should be rehashed
        """
        try:
            # Extract rounds from bcrypt hash format: $2b$12$...
            hash_rounds = int(hashed_password.split('$')[2])
            return hash_rounds < rounds
        except Exception as e:
            logger.warning(f"Could not determine hash rounds: {e}")
            return True


class PasswordSecurityManager:
    """
    Manages password security policies and operations.
    """
    
    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        check_common: bool = True
    ):
        """
        Initialize security manager with policies.
        
        Args:
            min_length: Minimum password length
            require_uppercase: Require uppercase letter
            require_lowercase: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            check_common: Check against common passwords
        """
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.check_common = check_common
    
    def validate_and_hash(self, password: str) -> Optional[str]:
        """
        Validate password and return hash if valid.
        
        Args:
            password: Password to validate and hash
        
        Returns:
            Password hash if valid, None if invalid
        """
        # Validate
        validation = PasswordValidator.validate_password(
            password,
            min_length=self.min_length,
            require_uppercase=self.require_uppercase,
            require_lowercase=self.require_lowercase,
            require_digit=self.require_digit,
            require_special=self.require_special
        )
        
        if not validation["valid"]:
            logger.warning(f"Password validation failed: {validation['errors']}")
            return None
        
        if self.check_common and PasswordValidator.is_common_password(password):
            logger.warning("Password is too common")
            return None
        
        # Hash
        try:
            return PasswordHasher.hash_password(password)
        except ValueError as e:
            logger.warning(f"Password hashing failed: {e}")
            return None
    
    def verify_and_update(
        self,
        password: str,
        stored_hash: str
    ) -> Dict[str, Any]:
        """
        Verify password and check if hash needs updating.
        
        Args:
            password: Password to verify
            stored_hash: Stored password hash
        
        Returns:
            Dictionary with verification result and rehash recommendation
        """
        verified = PasswordHasher.verify_password(password, stored_hash)
        needs_rehash = PasswordHasher.needs_rehash(stored_hash) if verified else False
        
        return {
            "verified": verified,
            "needs_rehash": needs_rehash,
            "new_hash": self.validate_and_hash(password) if needs_rehash else None
        }


if __name__ == "__main__":
    # Example usage
    manager = PasswordSecurityManager()
    
    # Validate password
    validation = PasswordValidator.validate_password("MySecureP@ssw0rd123!")
    print(f"Validation result: {validation}")
    
    # Hash password
    hashed = PasswordHasher.hash_password("MySecureP@ssw0rd123!")
    print(f"Hashed password: {hashed[:20]}...")
    
    # Verify password
    verified = PasswordHasher.verify_password("MySecureP@ssw0rd123!", hashed)
    print(f"Password verified: {verified}")
    
    # Check if needs rehash
    needs_rehash = PasswordHasher.needs_rehash(hashed)
    print(f"Needs rehash: {needs_rehash}")
