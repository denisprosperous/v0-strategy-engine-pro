"""
DataProviderAdapter: Free API/Future Paid Abstraction for Institutional Sniper
===========================================================
Handles wallet label lookups, token holders, DEX pools, transfers
Free: Etherscan, The Graph; Paid: Nansen, Arkham, DEXScreener
"""
import requests
from typing import Dict, List, Optional
from .config import InstitutionalSniperConfig

class DataProviderAdapter:
    def __init__(self, config: InstitutionalSniperConfig):
        self.config = config

    # Wallet Institutional Label
    def get_wallet_entity(self, address: str) -> Optional[Dict]:
        for entity, wallets in self.config.tier1_wallets.items():
            if address.lower() in [w.lower() for w in wallets]:
                return {'tier': 1, 'entity': entity, 'source': 'config'}
        for entity, wallets in self.config.tier2_wallets.items():
            if address.lower() in [w.lower() for w in wallets]:
                return {'tier': 2, 'entity': entity, 'source': 'config'}
        for entity, wallets in self.config.tier3_wallets.items():
            if address.lower() in [w.lower() for w in wallets]:
                return {'tier': 3, 'entity': entity, 'source': 'config'}
        return None

    # Token Holders
    def get_token_holders(self, token_addr: str) -> List[Dict]:
        url = f"https://api.etherscan.io/api?module=token&action=tokenholderlist&contractaddress={token_addr}&apikey={self.config.etherscan_api_key}"
        resp = requests.get(url)
        return resp.json()['result'] if 'result' in resp.json() else []

    # DEX Pools
    def get_new_pools(self, min_liq: float, max_liq: float) -> List[Dict]:
        query = '{ pools( first: 100, orderBy: createdAtTimestamp, orderDirection: desc, where: { totalValueLockedUSD_gte: "%s", totalValueLockedUSD_lte: "%s" } ) { id token0 {symbol} token1 {symbol} totalValueLockedUSD createdAtTimestamp } } }' % (min_liq, max_liq)
        resp = requests.post(self.config.the_graph_endpoint, json={"query": query})
        return resp.json()['data']['pools'] if 'data' in resp.json() else []

    # ERC20 Transfers
    def get_token_transfers(self, token_addr: str, from_block: int=0) -> List[Dict]:
        url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={token_addr}&startblock={from_block}&apikey={self.config.etherscan_api_key}"
        resp = requests.get(url)
        return resp.json()['result'] if 'result' in resp.json() else []
