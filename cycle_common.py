"""Shared read-only helpers for the Polygon atomic-cycle study (RECAP §5 item B).

READ-ONLY: only eth_call / eth_getLogs / eth_blockNumber. No signing, no tx, no private keys.
Execution lives in xend-arb; this repo only measures.

RPC: set POLYGON_RPC_URL (or RPC_URL); otherwise falls back to public endpoints.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode
from web3 import Web3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PUBLIC_RPCS = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon.drpc.org",
]

# --- Polygon (137) infra ---
UNI_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
QUOTER_V2 = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"

# --- Tokens (verified on-chain by cycle_discover.py) ---
USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"  # native USDC, 6 dec
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # bridged USDC.e, 6 dec
USDT0 = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"  # USDT0 (ex-USDT PoS), 6 dec

# --- Candidate pools ---
POOL_USDC_BRLA = "0x0e7754127dedd4097be750825dbb4669bc32c956"
POOL_BRZ_USDT0 = "0x4aF62A93775c093AF3e32949eF23C9A323D20817"
POOL_BRZ_BRLA = "0x6e05b2e9c6ccca3308a73f597b4c92ea4e6cfb86"
POOL_TESOURO = "0xc89f31f74573cc19fffc06108601c1ac71ba9735"

CS = Web3.to_checksum_address


def rpc_urls() -> list[str]:
    env = os.environ.get("POLYGON_RPC_URL") or os.environ.get("RPC_URL")
    return [env] if env else list(PUBLIC_RPCS)


def build_w3(url: str | None = None, timeout_s: int = 15) -> Web3:
    url = url or rpc_urls()[0]
    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": timeout_s}))
    try:
        from web3.middleware import ExtraDataToPOAMiddleware

        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        pass
    return w3


def selector(sig: str) -> bytes:
    return Web3.keccak(text=sig)[:4]


def encode(sig: str, in_types: list[str], args: list[Any]) -> bytes:
    return selector(sig) + (abi_encode(in_types, args) if in_types else b"")


def call(w3: Web3, to: str, sig: str, in_types: list[str], args: list[Any],
         out_types: list[str], block: int | str = "latest") -> tuple[Any, ...]:
    data = encode(sig, in_types, args)
    raw = w3.eth.call({"to": CS(to), "data": data}, block_identifier=block)
    return abi_decode(out_types, raw)


def try_call(w3: Web3, to: str, sig: str, in_types: list[str], args: list[Any],
             out_types: list[str], block: int | str = "latest") -> tuple[Any, ...] | None:
    try:
        return call(w3, to, sig, in_types, args, out_types, block)
    except Exception:
        return None


def multicall(w3: Web3, calls: list[tuple[str, bytes]], block: int | str = "latest"
              ) -> list[tuple[bool, bytes]]:
    """aggregate3 with allowFailure=True -> list of (success, returnData)."""
    data = encode("aggregate3((address,bool,bytes)[])", ["(address,bool,bytes)[]"],
                  [[(CS(t), True, cd) for t, cd in calls]])
    raw = w3.eth.call({"to": CS(MULTICALL3), "data": data}, block_identifier=block)
    (res,) = abi_decode(["(bool,bytes)[]"], raw)
    return [(bool(s), bytes(r)) for s, r in res]


def with_retry(fn, *a, tries: int = 3, delay: float = 1.0, **kw):
    last = None
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay * (2 ** i))
    raise last  # type: ignore[misc]


def v3_path(tokens: list[str], fees: list[int]) -> bytes:
    """Uniswap v3 packed path: token(20) fee(3) token(20) ..."""
    assert len(tokens) == len(fees) + 1
    out = b""
    for i, f in enumerate(fees):
        out += bytes.fromhex(CS(tokens[i])[2:]) + int(f).to_bytes(3, "big")
    return out + bytes.fromhex(CS(tokens[-1])[2:])
