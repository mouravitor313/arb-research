"""Per-chain config for the multi-chain read-only quoters (item 1: BTC/ETH/SOL vs OKX).

READ-ONLY. RPC override per chain via env: POLYGON_RPC_URL, ARBITRUM_RPC_URL, BASE_RPC_URL.
Addresses are canonical deployments; pools are discovered/validated by xvenue_discover.py.
"""

from __future__ import annotations

import os

CHAINS = {
    "ethereum": {
        "chain_id": 1,
        "rpcs": ["https://ethereum-rpc.publicnode.com", "https://eth.drpc.org"],
        "env": "ETHEREUM_RPC_URL",
        "v3_factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "quoter_v2": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        "native_okx": "ETH-USDT",
        "tokens": {
            "USDC": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
            "USDT": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
            "WBTC": ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
            "cbBTC": ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
            "WETH": ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
        },
    },
    "polygon": {
        "chain_id": 137,
        "rpcs": ["https://polygon-bor-rpc.publicnode.com", "https://polygon.drpc.org"],
        "env": "POLYGON_RPC_URL",
        "v3_factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "quoter_v2": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        "native_okx": "POL-USDT",  # gas token price source
        "tokens": {
            "USDC": ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
            "USDT": ("0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
            "WBTC": ("0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", 8),
            "WETH": ("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", 18),
        },
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpcs": ["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc"],
        "env": "ARBITRUM_RPC_URL",
        "v3_factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "quoter_v2": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        "native_okx": "ETH-USDT",
        "tokens": {
            "USDC": ("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
            "USDT": ("0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
            "WBTC": ("0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", 8),
            "WETH": ("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
        },
    },
    "base": {
        "chain_id": 8453,
        "rpcs": ["https://base-rpc.publicnode.com", "https://mainnet.base.org"],
        "env": "BASE_RPC_URL",
        "v3_factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
        "quoter_v2": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
        "native_okx": "ETH-USDT",
        "tokens": {
            "USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
            "cbBTC": ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
            "WETH": ("0x4200000000000000000000000000000000000006", 18),
        },
    },
}


def rpc_list(chain: str) -> list[str]:
    c = CHAINS[chain]
    env = os.environ.get(c["env"])
    return [env] if env else list(c["rpcs"])
