"""
InstitutionalSniperConfig: Free-Tier, Upgrade-Ready Configuration
================================================================
Handles: Etherscan, The Graph, public Web3 endpoints, Telegram
Manual institutional wallet bootstrap, hot upgrade to paid APIs
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class InstitutionalSniperConfig:
    etherscan_api_key: str = "YOUR_FREE_ETHERSCAN_KEY"
    the_graph_endpoint: str = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    public_rpc_urls: List[str] = field(default_factory=lambda: [
        "https://rpc.ankr.com/eth",
        "https://cloudflare-eth.com"
    ])
    telegram_bot_token: str = "YOUR_TELEGRAM_BOT_TOKEN"
    telegram_chat_id: str = "YOUR_TELEGRAM_CHAT_ID"

    tier1_wallets: Dict[str, List[str]] = field(default_factory=lambda: {
        'a16z_crypto': ['0x05e793ce0c6027323ac150f6d45c2344d28b6019'],
        'paradigm': ['0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2'],
        'polychain': ['0x6f50c6bff08ec925232937b204b0ae23c488402a'],
    })
    tier2_wallets: Dict[str, List[str]] = field(default_factory=lambda: {
        'jump_crypto': [],
        'wintermute': [],
    })
    tier3_wallets: Dict[str, List[str]] = field(default_factory=lambda: {
        'coinbase_ventures': [],
        'binance_labs': [],
    })
    use_nansen: bool = False  # Hot upgrade switch
    use_arkham: bool = False
    use_dexscreener: bool = False

    min_institutional_entities: int = 2
    min_aggregate_buy: float = 300000.0
    max_entity_concentration: float = 0.4
    max_position_size_pct: float = 0.015
    hard_stop_loss_pct: float = 0.25
    max_concurrent_positions: int = 3
    max_hold_time_hours: int = 72
    early_exit_multiplier: float = 1.8
    momentum_exit_multiplier: float = 3.0
