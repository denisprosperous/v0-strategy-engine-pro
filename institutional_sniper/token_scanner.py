"""
FreeTierDEXScanner: Real-Time Token Pool Monitor (The Graph, Free API)
=============================================================
Scans Uniswap V3 (and other DEX subgraphs) for new pools, liquidity, volume
Yields TokenCandidate objects for analysis
"""
import requests
import time
from typing import List, Dict, Generator
from datetime import datetime, timedelta

class TokenCandidate:
    def __init__(self, address, symbol, pool_address, liquidity_usd, dex, created_at, initial_txs):
        self.address = address
        self.symbol = symbol
        self.pool_address = pool_address
        self.liquidity_usd = liquidity_usd
        self.dex = dex
        self.created_at = created_at
        self.initial_txs = initial_txs

class FreeTierDEXScanner:
    def __init__(self, config):
        self.endpoint = config.the_graph_endpoint
        self.last_scan = datetime.utcnow() - timedelta(hours=1)
        self.scan_dex = ['uniswap_v3']
    def scan_new_pools(self, min_liq=100000, max_liq=2000000, poll_interval=30) -> Generator[TokenCandidate, None, None]:
        while True:
            new_ts = int(time.mktime(self.last_scan.timetuple()))
            query = '{ pools( first: 20, orderBy: createdAtTimestamp, orderDirection: desc, where: { createdAtTimestamp_gt: %d, totalValueLockedUSD_gte: "%s", totalValueLockedUSD_lte: "%s" } ) { id token0 {symbol id} token1 {symbol id} totalValueLockedUSD createdAtTimestamp } }' % (new_ts, min_liq, max_liq)
            resp = requests.post(self.endpoint, json={"query": query})
            pools = resp.json()['data']['pools'] if 'data' in resp.json() else []
            for pool in pools:
                created = datetime.utcfromtimestamp(int(pool['createdAtTimestamp']))
                # Select non-WETH token
                token_addr = pool['token0']['id'] if pool['token1']['symbol'] == 'WETH' else pool['token1']['id']
                candidate = TokenCandidate(
                    address=token_addr,
                    symbol=pool['token0']['symbol'] if pool['token1']['symbol'] == 'WETH' else pool['token1']['symbol'],
                    pool_address=pool['id'],
                    liquidity_usd=float(pool['totalValueLockedUSD']),
                    dex='uniswap_v3',
                    created_at=created,
                    initial_txs=[] # Add transaction probe if needed
                )
                yield candidate
            self.last_scan = datetime.utcnow()
            time.sleep(poll_interval)
