"""
Minimal Bitget REST client — pulls OHLCV candles for XAUTUSDT.
Uses public market-data endpoints (no auth needed for candles).
"""
import time
import hmac
import hashlib
import base64
import requests
from typing import List, Dict
import config


class BitgetClient:
    def __init__(self):
        self.base_url = config.REST_BASE_URL
        self.session = requests.Session()

    def _get(self, path: str, params: dict) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "00000":
            raise RuntimeError(f"Bitget API error: {data}")
        return data["data"]

    def get_candles(self, granularity: str, limit: int = 200) -> List[Dict]:
        """
        granularity: '1H', '4H' etc per Bitget's kline granularity spec.
        Returns list of dicts oldest -> newest:
        {ts, open, high, low, close, volume}
        """
        gran_map = {"1H": "1H", "4H": "4H", "15m": "15m"}
        params = {
            "symbol": config.SYMBOL,
            "granularity": gran_map.get(granularity, granularity),
            "limit": str(limit),
            "productType": config.PRODUCT_TYPE,
        }
        raw = self._get("/api/v2/mix/market/candles", params)
        candles = []
        for row in raw:
            candles.append({
                "ts": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        candles.sort(key=lambda c: c["ts"])
        return candles

    def get_ticker(self) -> Dict:
        params = {"symbol": config.SYMBOL, "productType": config.PRODUCT_TYPE}
        raw = self._get("/api/v2/mix/market/ticker", params)
        row = raw[0] if isinstance(raw, list) else raw
        return {
            "last_price": float(row["lastPr"]),
            "ts": int(row.get("ts", time.time() * 1000)),
        }

    # Signed request helper kept for future use (e.g. account/positions),
    # not required for signals-only mode.
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        message = f"{timestamp}{method}{request_path}{body}"
        mac = hmac.new(
            config.BITGET_API_SECRET.encode(), message.encode(), hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
