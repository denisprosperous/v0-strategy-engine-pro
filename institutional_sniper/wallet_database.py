"""
InstitutionalWalletDatabase: Curated Institutional Wallets for Sniper Strategy
============================================================
Bootstrap with manual entries; supports updates from public sources
Tiered lookup, instant entity/tier recognition
"""
import json
import os
from typing import Dict, Optional, List
from datetime import datetime

class InstitutionalWalletDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "data/institutional_wallets.json"
        self.wallets = self._load_database()
        self.last_updated = datetime.now()

    def _load_database(self) -> Dict:
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                return json.load(f)
        else:
            return self._initialize_default_database()

    def _initialize_default_database(self) -> Dict:
        return {
            'tier1': {
                'a16z_crypto': {'wallets': ['0x05e793ce0c6027323ac150f6d45c2344d28b6019'], 'verified': True},
                'paradigm': {'wallets': ['0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2'], 'verified': True},
                'polychain': {'wallets': ['0x6f50c6bff08ec925232937b204b0ae23c488402a'], 'verified': True},
            },
            'tier2': {},
            'tier3': {}
        }

    def is_institutional_wallet(self, address: str) -> Optional[Dict]:
        address_lower = address.lower()
        for tier_name, tier_data in self.wallets.items():
            for entity_name, entity_data in tier_data.items():
                if address_lower in [w.lower() for w in entity_data.get('wallets', [])]:
                    return {
                        'tier': tier_name,
                        'entity': entity_name,
                        'verified': entity_data.get('verified', False)
                    }
        return None

    def add_wallet(self, tier: str, entity: str, address: str, verified: bool = False):
        if tier not in self.wallets:
            self.wallets[tier] = {}
        if entity not in self.wallets[tier]:
            self.wallets[tier][entity] = {'wallets': [], 'verified': verified}
        self.wallets[tier][entity]['wallets'].append(address)
        self._save_database()

    def _save_database(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.wallets, f, indent=2)
