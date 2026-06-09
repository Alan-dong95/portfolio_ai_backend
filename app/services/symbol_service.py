from __future__ import annotations

import re
from typing import Any

from app.schemas.symbol import SymbolInfo

# kind: stock | etf | crypto | watchlist
_SYMBOL_REGISTRY: dict[str, dict[str, Any]] = {
    "301392": {
        "kind": "stock",
        "name_en": "Huicheng Vacuum",
        "name_zh": "汇成真空",
    },
    "588810": {
        "kind": "etf",
        "name_en": "STAR Market 50 ETF",
        "name_zh": "科创50ETF",
    },
    "588000": {
        "kind": "etf",
        "name_en": "STAR Market ETF",
        "name_zh": "科创50ETF",
    },
    "510300": {
        "kind": "etf",
        "name_en": "CSI 300 ETF",
        "name_zh": "沪深300ETF",
    },
    "159915": {
        "kind": "etf",
        "name_en": "ChiNext ETF",
        "name_zh": "创业板ETF",
    },
    "NVDA": {
        "kind": "stock",
        "name_en": "NVIDIA",
        "name_zh": "英伟达",
    },
    "AAPL": {
        "kind": "stock",
        "name_en": "Apple",
        "name_zh": "苹果",
    },
    "MSFT": {
        "kind": "stock",
        "name_en": "Microsoft",
        "name_zh": "微软",
    },
    "GOOGL": {
        "kind": "stock",
        "name_en": "Alphabet",
        "name_zh": "谷歌",
    },
    "GOOG": {
        "kind": "stock",
        "name_en": "Alphabet",
        "name_zh": "谷歌",
    },
    "META": {
        "kind": "stock",
        "name_en": "Meta",
        "name_zh": "Meta",
    },
    "TSM": {
        "kind": "stock",
        "name_en": "TSMC",
        "name_zh": "台积电",
    },
    "AMD": {
        "kind": "stock",
        "name_en": "AMD",
        "name_zh": "AMD",
    },
    "AMZN": {
        "kind": "stock",
        "name_en": "Amazon",
        "name_zh": "亚马逊",
    },
    "QQQ": {
        "kind": "etf",
        "name_en": "Invesco QQQ Trust",
        "name_zh": "纳指100ETF",
    },
    "SPY": {
        "kind": "etf",
        "name_en": "SPDR S&P 500 ETF",
        "name_zh": "标普500ETF",
    },
    "VOO": {
        "kind": "etf",
        "name_en": "Vanguard S&P 500 ETF",
        "name_zh": "标普500ETF",
    },
    "SOXX": {
        "kind": "etf",
        "name_en": "iShares Semiconductor ETF",
        "name_zh": "半导体ETF",
    },
    "BTC": {
        "kind": "crypto",
        "name_en": "Bitcoin",
        "name_zh": "比特币",
    },
    "BTC-USD": {
        "kind": "crypto",
        "name_en": "Bitcoin",
        "name_zh": "比特币",
    },
    "ETH": {
        "kind": "crypto",
        "name_en": "Ethereum",
        "name_zh": "以太坊",
    },
    "ETH-USD": {
        "kind": "crypto",
        "name_en": "Ethereum",
        "name_zh": "以太坊",
    },
}


def _normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    code = language.strip().lower().replace("_", "-").split("-")[0]
    return "zh" if code == "zh" else "en"


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _infer_kind(symbol: str) -> str:
    sym = _normalize_symbol(symbol)
    if sym.endswith("-USD") or sym in {"BTC", "ETH", "SOL", "DOGE", "XRP"}:
        return "crypto"
    if re.fullmatch(r"\d{6}", sym):
        if sym.startswith(("15", "16", "51", "56", "58")):
            return "etf"
        return "stock"
    if len(sym) <= 5 and sym.isalpha():
        return "stock"
    return "watchlist"


def _name_for_entry(entry: dict[str, Any], language: str) -> str:
    if language == "zh":
        return entry.get("name_zh") or entry.get("name_en") or ""
    return entry.get("name_en") or entry.get("name_zh") or ""


def lookup_symbol(symbol: str, *, language: str = "en") -> SymbolInfo:
    lang = _normalize_language(language)
    key = _normalize_symbol(symbol)
    base = key.split("-")[0]

    entry = _SYMBOL_REGISTRY.get(key) or _SYMBOL_REGISTRY.get(base)
    if entry is None:
        return SymbolInfo(
            symbol=key,
            name=key,
            kind=_infer_kind(key),
        )

    name = _name_for_entry(entry, lang) or key
    return SymbolInfo(
        symbol=key,
        name=name,
        kind=entry.get("kind") or _infer_kind(key),
    )


def lookup_symbols(symbols: list[str], *, language: str = "en") -> list[SymbolInfo]:
    seen: set[str] = set()
    results: list[SymbolInfo] = []
    for raw in symbols:
        key = _normalize_symbol(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(lookup_symbol(key, language=language))
    return results
