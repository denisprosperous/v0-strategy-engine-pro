"""
SmartMoneyDetector: Institutional Accumulation Engine (Free-Tier)
==========================================================
Detects coordination, large buys, tiered entity signals using free/curated APIs
Upgrade-ready for Nansen, Arkham, DEXScreener
"""
from .config import InstitutionalSniperConfig
from .free_tier_adapters import DataProviderAdapter
from .wallet_database import InstitutionalWalletDatabase
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

class AccumulationSignal:
    def __init__(self, entities: List[Dict], token_address: str, total_buy_volume: float, confidence: float, tier1_count: int, tier2_count: int, tier3_count: int):
        self.entities = entities
        self.token_address = token_address
        self.total_buy_volume = total_buy_volume
        self.confidence = confidence
        self.tier1_count = tier1_count
        self.tier2_count = tier2_count
        self.tier3_count = tier3_count

class SmartMoneyDetector:
    def __init__(self, config: InstitutionalSniperConfig):
        self.config = config
        self.data_provider = DataProviderAdapter(config)
        self.wallet_db = InstitutionalWalletDatabase()

    def detect_institutional_accumulation(self, token_address: str, lookback_hours: int = 12) -> Optional[AccumulationSignal]:
        current_block = self._get_current_block()
        from_block = max(0, current_block - int((lookback_hours*240)))  # ~15s block
        transfers = self.data_provider.get_token_transfers(token_address, from_block)
        buys = self._filter_significant_buys(transfers)
        entity_signals = []
        buy_total = 0
        tier1, tier2, tier3 = 0, 0, 0
        for t in buys:
            info = self.wallet_db.is_institutional_wallet(t['to'])
            if info:
                buy_total += float(t['value'])
                entity_signals.append(info)
                if info['tier'] == 'tier1': tier1 += 1
                elif info['tier'] == 'tier2': tier2 += 1
                elif info['tier'] == 'tier3': tier3 += 1
        confidence = self._score_confidence(entity_signals, buy_total)
        if len(entity_signals) >= self.config.min_institutional_entities:
            return AccumulationSignal(entity_signals, token_address, buy_total, confidence, tier1, tier2, tier3)
        return None

    def _filter_significant_buys(self, transfers: List[Dict]) -> List[Dict]:
        filtered = [t for t in transfers if t.get('value') and float(t['value']) >= 10000]  # Over $10K
        return filtered
    def _get_current_block(self):
        # Placeholder: Use public RPC or Etherscan to get number
        return 19600000
    def _score_confidence(self, entities, buy_total):
        # Simple: tier1 entities + buy volume, upgrades with paid APIs
        tier1_count = sum(1 for e in entities if e['tier'] == 'tier1')
        tier2_count = sum(1 for e in entities if e['tier'] == 'tier2')
        tier3_count = sum(1 for e in entities if e['tier'] == 'tier3')
        score = 0.5 * tier1_count + 0.3 * tier2_count + 0.2 * tier3_count + min(0.5, buy_total/500000)
        return min(1.0, score)
