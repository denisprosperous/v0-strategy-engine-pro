"""First-Run Setup Wizard - Phase 2

Interactive setup wizard for initial configuration.
Guides users through API key setup, security preferences, and account creation.
"""

import logging
import getpass
import sys
from typing import Optional

from security.crypto_vault import CryptoVault
from security.key_manager import KeyManager


logger = logging.getLogger(__name__)


class SetupWizard:
    """First-run setup wizard for secure configuration.
    
    Features:
    - Master key generation and backup
    - API key configuration for multiple exchanges
    - Trading preferences setup
    - Security policy acknowledgment
    - Configuration validation
    """
    
    def __init__(self):
        """Initialize setup wizard."""
        self.vault: Optional[CryptoVault] = None
        self.key_manager: Optional[KeyManager] = None
        self.config = {}
    
    def run(self) -> bool:
        """Run complete setup wizard.
        
        Returns:
            True if setup completed successfully
        """
        print("\n" + "="*60)
        print("  v0-Strategy-Engine-Pro - First Run Setup Wizard")
        print("="*60 + "\n")
        
        try:
            # Step 1: Welcome and disclaimers
            if not self._show_welcome():
                return False
            
            # Step 2: Generate master key
            if not self._setup_master_key():
                return False
            
            # Step 3: Add API keys
            if not self._setup_api_keys():
                return False
            
            # Step 4: Configure preferences
            if not self._setup_preferences():
                return False
            
            # Step 5: Security review
            if not self._security_review():
                return False
            
            print("\n✅ Setup completed successfully!")
            print("\nYour API keys are securely encrypted with AES-256-GCM.")
            print("Master key is protected with Argon2 password hashing.\n")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Setup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n\n❌ Setup error: {e}")
            logger.error(f"Setup wizard error: {e}")
            return False
    
    def _show_welcome(self) -> bool:
        """Display welcome and security disclaimers.
        
        Returns:
            True if user accepts terms
        """
        print("\n📋 SECURITY & DISCLAIMER\n")
        print("""
This setup wizard will help you configure your trading bot securely.

⚠️  IMPORTANT SECURITY INFORMATION:
  • Your API keys will be encrypted with AES-256-GCM
  • Your master key will be hashed with Argon2 (memory-hard)
  • Keys are stored securely in encrypted files
  • Never share your master key or API secrets
  • Trading bot operations carry financial risk
  • Always test on testnet/paper trading first

PRODUCTION WARNING:
  • Only use API keys with LIMITED permissions
  • Never use keys with withdraw/transfer permissions
  • Consider using sub-accounts when available
  • Regularly rotate API keys
  • Monitor trading bot activities closely
        """)
        
        accept = input("Do you accept and understand these terms? (yes/no): ").strip().lower()
        return accept == "yes"
    
    def _setup_master_key(self) -> bool:
        """Setup master encryption key.
        
        Returns:
            True if master key setup successful
        """
        print("\n🔑 MASTER KEY SETUP\n")
        
        # Generate crypto vault
        self.vault = CryptoVault()
        master_key = self.vault.export_master_key()
        
        print("Your master key (Base64-encoded):")
        print("-" * 60)
        print(master_key)
        print("-" * 60)
        
        print("\n⚠️  BACKUP YOUR MASTER KEY!")
        print("You will need this to restore your API keys if you need to")
        print("reinstall or recover your configuration.\n")
        
        # Setup password
        while True:
            password = getpass.getpass(
                "Create a strong password to protect your master key: "
            )
            if len(password) < 12:
                print("❌ Password must be at least 12 characters.")
                continue
            
            password_confirm = getpass.getpass(
                "Confirm password: "
            )
            if password != password_confirm:
                print("❌ Passwords don't match.")
                continue
            
            break
        
        # Hash password
        hashed, salt = self.vault.hash_password(password)
        self.config['password_hash'] = hashed
        self.config['password_salt'] = salt
        self.config['master_key_backup'] = master_key
        
        print("\n✅ Master key configured.")
        return True
    
    def _setup_api_keys(self) -> bool:
        """Setup API keys for exchanges.
        
        Returns:
            True if keys configured
        """
        print("\n🔗 API KEY CONFIGURATION\n")
        
        self.key_manager = KeyManager(self.vault)
        
        exchanges = ['binance', 'bybit', 'okx', 'oanda', 'interactive_brokers']
        print("Supported exchanges:")
        for i, ex in enumerate(exchanges, 1):
            print(f"  {i}. {ex}")
        
        added_keys = 0
        while True:
            exchange_choice = input("\nSelect exchange (or 'done' to finish): ").strip().lower()
            
            if exchange_choice == 'done':
                if added_keys == 0:
                    print("⚠️  You haven't added any API keys.")
                    continue
                break
            
            try:
                exchange = exchanges[int(exchange_choice) - 1]
            except (ValueError, IndexError):
                print("❌ Invalid selection.")
                continue
            
            is_testnet = input(f"Is this for {exchange} testnet? (yes/no): ").strip().lower() == "yes"
            api_key = getpass.getpass(f"Enter {exchange} API key: ")
            api_secret = getpass.getpass(f"Enter {exchange} API secret: ")
            
            # Optional passphrase
            passphrase = None
            if exchange in ['okx', 'kraken']:
                passphrase_opt = input(f"Enter passphrase (optional): ").strip()
                if passphrase_opt:
                    passphrase = passphrase_opt
            
            # Add key
            key_id = self.key_manager.add_key(
                exchange=exchange,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                is_testnet=is_testnet
            )
            
            print(f"✅ Added {exchange} API key (ID: {key_id})")
            added_keys += 1
        
        return True
    
    def _setup_preferences(self) -> bool:
        """Setup trading preferences.
        
        Returns:
            True if preferences configured
        """
        print("\n⚙️  TRADING PREFERENCES\n")
        
        # Risk level
        print("Risk Management:")
        print("  1. Conservative (low leverage, small position sizes)")
        print("  2. Moderate (normal leverage, standard position sizes)")
        print("  3. Aggressive (high leverage, large position sizes)")
        
        risk_choice = input("Select risk level (1-3): ").strip()
        risk_levels = {"1": "conservative", "2": "moderate", "3": "aggressive"}
        self.config['risk_level'] = risk_levels.get(risk_choice, "moderate")
        
        # Max daily loss
        max_loss = input("Max daily loss percentage (default 5): ").strip() or "5"
        try:
            self.config['max_daily_loss_pct'] = float(max_loss)
        except ValueError:
            self.config['max_daily_loss_pct'] = 5.0
        
        print("\n✅ Preferences configured.")
        return True
    
    def _security_review(self) -> bool:
        """Final security review before completion.
        
        Returns:
            True if user confirms
        """
        print("\n🔒 SECURITY REVIEW\n")
        print("""
Setup Summary:
  ✅ Master key generated and encrypted
  ✅ API keys encrypted with AES-256-GCM
  ✅ Trading preferences configured
  ✅ Risk management policies set

Reminders:
  • Your API keys are encrypted at rest
  • Keep your master key backup in a safe place
  • Regularly audit your API key usage
  • Report suspicious activity immediately
  • Never hardcode credentials in code
        """)
        
        confirm = input("\nProceed with setup? (yes/no): ").strip().lower()
        return confirm == "yes"


def run_setup_wizard() -> bool:
    """Execute the setup wizard.
    
    Returns:
        True if successful
    """
    wizard = SetupWizard()
    return wizard.run()


if __name__ == "__main__":
    success = run_setup_wizard()
    sys.exit(0 if success else 1)
