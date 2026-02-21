"""
bingx_client.py — Cliente completo para la API de BingX Perpetual Futures

Ref: https://bingx-api.github.io/docs/#/en-us/swapV2/

Autenticación: HMAC-SHA256 sobre los parámetros ordenados.
Todos los params (incluyendo timestamp y signature) van en el query string,
incluso para peticiones POST.  El body siempre va vacío.
"""

import hashlib
import hmac
import http.client
import json
import time
import urllib.parse


# ──────────────────────────────────────────────────────────────────────────────
# Excepción propia
# ──────────────────────────────────────────────────────────────────────────────

class BingXError(Exception):
    """Excepción lanzada por errores de la API de BingX."""
    def __init__(self, code: int, msg: str):
        self.code = code
        super().__init__(f"BingX [{code}]: {msg}")


# ──────────────────────────────────────────────────────────────────────────────
# Cliente principal
# ──────────────────────────────────────────────────────────────────────────────

class BingXClient:
    """
    Cliente REST para BingX Perpetual Swap API.
    Usa únicamente módulos de la stdlib (http.client, hmac, hashlib).
    """

    HOST    = "open-api.bingx.com"
    TIMEOUT = 12  # segundos

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise BingXError(0, "API Key y Secret son obligatorios")
        self.api_key    = api_key.strip()
        self.api_secret = api_secret.strip()

    # ──────────────────────────────────────────
    # Firma y HTTP interno
    # ──────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        """Añade timestamp y firma HMAC-SHA256."""
        p = dict(params)
        p["timestamp"] = int(time.time() * 1000)
        # La firma se calcula sobre los params ordenados
        raw = "&".join(f"{k}={v}" for k, v in sorted(p.items()))
        sig = hmac.new(
            self.api_secret.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        p["signature"] = sig
        return p

    def _request(
        self,
        method:  str,
        path:    str,
        params:  dict = None,
        signed:  bool = False,
    ) -> object:
        """Realiza la petición HTTP y devuelve data del JSON de respuesta."""
        p = dict(params or {})
        if signed:
            p = self._sign(p)

        query = urllib.parse.urlencode(p)
        url   = f"{path}?{query}" if query else path

        conn = http.client.HTTPSConnection(self.HOST, timeout=self.TIMEOUT)
        headers = {
            "X-BX-APIKEY":  self.api_key,
            "Content-Type": "application/json",
        }
        try:
            if method.upper() in ("GET", "DELETE"):
                conn.request(method.upper(), url, headers=headers)
            else:
                # POST: params en query string, body vacío
                conn.request("POST", url, body=b"", headers=headers)

            resp = conn.getresponse()
            raw  = resp.read().decode("utf-8")
        finally:
            conn.close()

        try:
            data = json.loads(raw)
        except Exception:
            raise BingXError(-1, f"Respuesta no JSON: {raw[:300]}")

        code = data.get("code", -1)
        if code != 0:
            raise BingXError(code, data.get("msg", raw[:200]))

        return data.get("data", data)

    # ──────────────────────────────────────────
    # Cuenta / Balance
    # ──────────────────────────────────────────

    def ping(self) -> bool:
        """Verifica conectividad básica."""
        try:
            self._request("GET", "/openApi/swap/v2/server/time")
            return True
        except Exception:
            return False

    def get_balance(self) -> dict:
        """
        Balance de la cuenta.
        Devuelve el sub-dict 'balance' con:
          userId, asset, balance, equity, unrealizedProfit, realisedProfit,
          availableMargin, usedMargin, freezedMargin
        """
        data = self._request("GET", "/openApi/swap/v2/user/balance", signed=True)
        # La respuesta real es {"balance": {...}}
        if isinstance(data, dict) and "balance" in data:
            return data["balance"]
        return data

    def get_uid(self) -> str:
        """UID numérico del usuario."""
        try:
            data = self._request("GET", "/openApi/account/v1/uid", signed=True)
            if isinstance(data, dict):
                return str(data.get("uid", data.get("userId", "—")))
            return str(data)
        except Exception:
            return "—"

    # ──────────────────────────────────────────
    # Datos de mercado
    # ──────────────────────────────────────────

    def get_price(self, symbol: str) -> float:
        """Precio mark actual del símbolo."""
        data = self._request(
            "GET", "/openApi/swap/v2/quote/price", {"symbol": symbol}
        )
        return float(data.get("price", 0))

    def get_ticker(self, symbol: str) -> dict:
        """Estadísticas 24h."""
        return self._request(
            "GET", "/openApi/swap/v2/quote/ticker", {"symbol": symbol}
        )

    def get_klines(
        self, symbol: str, interval: str = "15m", limit: int = 150
    ) -> list:
        """
        Velas OHLCV.
        interval: 1m 3m 5m 15m 30m 1h 2h 4h 6h 12h 1d 3d 1w 1M
        Devuelve lista de dicts con claves: o h l c v time
        """
        data = self._request(
            "GET",
            "/openApi/swap/v3/quote/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        return data if isinstance(data, list) else []

    def get_funding_rate(self, symbol: str) -> float:
        """Tasa de financiamiento actual."""
        try:
            data = self._request(
                "GET", "/openApi/swap/v2/quote/fundingRate", {"symbol": symbol}
            )
            rate = data.get("fundingRate") if isinstance(data, dict) else None
            return float(rate) if rate is not None else 0.0
        except Exception:
            return 0.0

    # ──────────────────────────────────────────
    # Posiciones abiertas
    # ──────────────────────────────────────────

    def get_positions(self, symbol: str = None) -> list:
        """Lista de posiciones abiertas (qty != 0)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        data = self._request(
            "GET", "/openApi/swap/v2/user/positions", params=params, signed=True
        )
        positions = data if isinstance(data, list) else []
        # Filtrar las que tienen posición real
        return [p for p in positions if float(p.get("positionAmt", 0)) != 0]

    # ──────────────────────────────────────────
    # Configurar apalancamiento / margen
    # ──────────────────────────────────────────

    def set_leverage(self, symbol: str, leverage: int) -> None:
        """Establece el apalancamiento para LONG y SHORT."""
        for side in ("LONG", "SHORT"):
            try:
                self._request(
                    "POST",
                    "/openApi/swap/v2/trade/leverage",
                    {"symbol": symbol, "side": side, "leverage": leverage},
                    signed=True,
                )
            except BingXError as e:
                # Ignorar error de "leverage sin cambio"
                if e.code not in (80012, 80013):
                    raise

    def set_margin_type(self, symbol: str, margin_type: str) -> None:
        """Cambia el tipo de margen: ISOLATED o CROSSED."""
        try:
            self._request(
                "POST",
                "/openApi/swap/v2/trade/marginType",
                {"symbol": symbol, "marginType": margin_type},
                signed=True,
            )
        except BingXError as e:
            # Ignorar si ya está configurado
            if e.code not in (80012, 80013, 80014):
                raise

    # ──────────────────────────────────────────
    # Órdenes
    # ──────────────────────────────────────────

    def place_market_order(
        self,
        symbol:        str,
        side:          str,   # BUY | SELL
        position_side: str,   # LONG | SHORT
        quantity:      float,
        stop_loss:     float = None,
        take_profit:   float = None,
    ) -> dict:
        """
        Orden de mercado con TP/SL opcionales adjuntos.
        Devuelve el dict de la orden creada.
        """
        params = {
            "symbol":       symbol,
            "side":         side,
            "positionSide": position_side,
            "type":         "MARKET",
            "quantity":     f"{quantity:.4f}",
        }
        if take_profit:
            params["takeProfit"] = json.dumps({
                "type":        "TAKE_PROFIT_MARKET",
                "stopPrice":   f"{take_profit:.2f}",
                "workingType": "MARK_PRICE",
            })
        if stop_loss:
            params["stopLoss"] = json.dumps({
                "type":        "STOP_MARKET",
                "stopPrice":   f"{stop_loss:.2f}",
                "workingType": "MARK_PRICE",
            })
        return self._request(
            "POST", "/openApi/swap/v2/trade/order", params, signed=True
        )

    def close_position(
        self, symbol: str, position_side: str, quantity: float
    ) -> dict:
        """Cierra una posición en su totalidad con orden de mercado."""
        close_side = "SELL" if position_side == "LONG" else "BUY"
        return self.place_market_order(symbol, close_side, position_side, quantity)

    def get_open_orders(self, symbol: str = None) -> list:
        """Órdenes pendientes (LIMIT / TP / SL sin ejecutar)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        data = self._request(
            "GET", "/openApi/swap/v2/trade/openOrders",
            params=params, signed=True,
        )
        return data if isinstance(data, list) else []

    def cancel_order(self, symbol: str, order_id) -> dict:
        return self._request(
            "DELETE",
            "/openApi/swap/v2/trade/order",
            {"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_trade_history(self, symbol: str, limit: int = 50) -> list:
        """Historial de órdenes cerradas."""
        try:
            data = self._request(
                "GET",
                "/openApi/swap/v2/trade/allOrders",
                {"symbol": symbol, "limit": limit},
                signed=True,
            )
            return data if isinstance(data, list) else []
        except Exception:
            return []


# ──────────────────────────────────────────────────────────────────────────────
# Indicadores técnicos (stdlib, sin numpy)
# ──────────────────────────────────────────────────────────────────────────────

def _ema_series(prices: list, n: int) -> list:
    """Serie EMA completa."""
    if len(prices) < n:
        return prices[:]
    k   = 2.0 / (n + 1)
    out = [sum(prices[:n]) / n]
    for p in prices[n:]:
        out.append(p * k + out[-1] * (1.0 - k))
    return out


def _rsi(closes: list, n: int = 14) -> float:
    """RSI del último valor en la serie."""
    if len(closes) < n + 2:
        return 50.0
    deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    gains  = [max(d, 0.0) for d in deltas]
    losses = [abs(min(d, 0.0)) for d in deltas]
    ag = sum(gains[:n])  / n
    al = sum(losses[:n]) / n
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i])  / n
        al = (al * (n - 1) + losses[i]) / n
    if al == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + ag / al))


def _atr(highs: list, lows: list, closes: list, n: int = 14) -> float:
    """ATR del último período."""
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return 0.0
    atr = sum(trs[:n]) / min(n, len(trs))
    for i in range(n, len(trs)):
        atr = (atr * (n - 1) + trs[i]) / n
    return atr


def _kf(k, full, short, default=0.0):
    """Extrae un campo de una vela manejando distintos nombres de campo de BingX."""
    v = k.get(full, k.get(short, default))
    return float(v) if v not in (None, "", "null") else default


def generate_signal(klines: list) -> tuple:
    """
    Genera señal de trading basada en EMA9/EMA21 + RSI14 + ATR14.
    Maneja los formatos de campo de BingX v2 (o/h/l/c) y v3 (open/high/low/close).

    Retorna (signal, rsi, atr) donde signal es:
      'BUY'  → abrir LONG
      'SELL' → abrir SHORT
      None   → sin señal
    """
    if len(klines) < 30:
        return None, 50.0, 0.0

    opens  = [_kf(k, "open",  "o")  for k in klines]
    highs  = [_kf(k, "high",  "h")  for k in klines]
    lows   = [_kf(k, "low",   "l")  for k in klines]
    closes = [_kf(k, "close", "c")  for k in klines]

    ema9  = _ema_series(closes, 9)
    ema21 = _ema_series(closes, 21)
    rsi   = _rsi(closes, 14)
    atr   = _atr(highs, lows, closes, 14)

    # Cruce EMA: índices -1 y -2 de las series (alineadas por longitud mínima)
    min_len = min(len(ema9), len(ema21))
    e9_now,  e9_prev  = ema9[min_len - 1],  ema9[min_len - 2]
    e21_now, e21_prev = ema21[min_len - 1], ema21[min_len - 2]

    # Señal LONG: cruce alcista + RSI entre 40-70
    if e9_prev <= e21_prev and e9_now > e21_now and 40 < rsi < 70:
        return "BUY", rsi, atr

    # Señal SHORT: cruce bajista + RSI entre 30-60
    if e9_prev >= e21_prev and e9_now < e21_now and 30 < rsi < 60:
        return "SELL", rsi, atr

    return None, rsi, atr


def calc_quantity(
    available_margin: float,
    risk_pct:         float,
    entry_price:      float,
    stop_loss:        float,
    leverage:         int,
    min_qty:          float = 0.001,
) -> float:
    """
    Calcula la cantidad a operar basada en riesgo %.
    risk_pct: porcentaje del balance a arriesgar (ej. 1.0 → 1 %).
    """
    if entry_price <= 0 or stop_loss <= 0:
        return min_qty
    price_risk = abs(entry_price - stop_loss)
    if price_risk == 0:
        return min_qty
    risk_usdt = available_margin * (risk_pct / 100.0)
    qty = risk_usdt / price_risk
    qty = max(qty, min_qty)
    return round(qty, 4)
