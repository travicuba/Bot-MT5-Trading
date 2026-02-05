# indicators/technical_indicators.py

"""
Módulo para cálculos técnicos adicionales en Python
usando los datos crudos de velas del market_data.json
"""

import numpy as np


def calculate_support_resistance(candles, lookback=20):
    """
    Identifica niveles de soporte y resistencia basados en las últimas velas
    
    Args:
        candles: Lista de diccionarios con datos de velas
        lookback: Número de velas a analizar
    
    Returns:
        dict con 'support' y 'resistance'
    """
    if not candles or len(candles) < lookback:
        return {"support": None, "resistance": None}
    
    # Obtener últimas N velas
    recent_candles = candles[:lookback]
    
    # Extraer highs y lows
    highs = [c["high"] for c in recent_candles]
    lows = [c["low"] for c in recent_candles]
    
    # Resistencia: máximo de los máximos
    resistance = max(highs)
    
    # Soporte: mínimo de los mínimos
    support = min(lows)
    
    return {
        "support": support,
        "resistance": resistance,
        "range": resistance - support
    }


def detect_candlestick_patterns(candles):
    """
    Detecta patrones de velas japonesas comunes
    
    Args:
        candles: Lista de diccionarios con datos de velas (más reciente primero)
    
    Returns:
        dict con patrones detectados
    """
    if not candles or len(candles) < 3:
        return {"pattern": "NONE", "signal": "NEUTRAL"}
    
    # Últimas 3 velas (0 = más reciente)
    c0 = candles[0]  # Actual
    c1 = candles[1]  # Anterior
    c2 = candles[2]  # Hace 2
    
    patterns = {
        "pattern": "NONE",
        "signal": "NEUTRAL",
        "strength": 0
    }
    
    # Helper functions
    def is_bullish(candle):
        return candle["close"] > candle["open"]
    
    def is_bearish(candle):
        return candle["close"] < candle["open"]
    
    def body_size(candle):
        return abs(candle["close"] - candle["open"])
    
    def upper_wick(candle):
        return candle["high"] - max(candle["open"], candle["close"])
    
    def lower_wick(candle):
        return min(candle["open"], candle["close"]) - candle["low"]
    
    # ========== HAMMER (Alcista) ==========
    if is_bullish(c0):
        body = body_size(c0)
        lower = lower_wick(c0)
        upper = upper_wick(c0)
        
        if lower > body * 2 and upper < body * 0.5:
            patterns["pattern"] = "HAMMER"
            patterns["signal"] = "BULLISH"
            patterns["strength"] = 0.7
            return patterns
    
    # ========== SHOOTING STAR (Bajista) ==========
    if is_bearish(c0):
        body = body_size(c0)
        upper = upper_wick(c0)
        lower = lower_wick(c0)
        
        if upper > body * 2 and lower < body * 0.5:
            patterns["pattern"] = "SHOOTING_STAR"
            patterns["signal"] = "BEARISH"
            patterns["strength"] = 0.7
            return patterns
    
    # ========== ENGULFING BULLISH ==========
    if is_bearish(c1) and is_bullish(c0):
        if c0["close"] > c1["open"] and c0["open"] < c1["close"]:
            patterns["pattern"] = "ENGULFING_BULLISH"
            patterns["signal"] = "BULLISH"
            patterns["strength"] = 0.8
            return patterns
    
    # ========== ENGULFING BEARISH ==========
    if is_bullish(c1) and is_bearish(c0):
        if c0["close"] < c1["open"] and c0["open"] > c1["close"]:
            patterns["pattern"] = "ENGULFING_BEARISH"
            patterns["signal"] = "BEARISH"
            patterns["strength"] = 0.8
            return patterns
    
    # ========== DOJI (Indecisión) ==========
    body = body_size(c0)
    total_range = c0["high"] - c0["low"]
    
    if total_range > 0 and body / total_range < 0.1:
        patterns["pattern"] = "DOJI"
        patterns["signal"] = "NEUTRAL"
        patterns["strength"] = 0.5
        return patterns
    
    # ========== THREE WHITE SOLDIERS (Muy alcista) ==========
    if is_bullish(c0) and is_bullish(c1) and is_bullish(c2):
        if c0["close"] > c1["close"] > c2["close"]:
            patterns["pattern"] = "THREE_WHITE_SOLDIERS"
            patterns["signal"] = "BULLISH"
            patterns["strength"] = 0.9
            return patterns
    
    # ========== THREE BLACK CROWS (Muy bajista) ==========
    if is_bearish(c0) and is_bearish(c1) and is_bearish(c2):
        if c0["close"] < c1["close"] < c2["close"]:
            patterns["pattern"] = "THREE_BLACK_CROWS"
            patterns["signal"] = "BEARISH"
            patterns["strength"] = 0.9
            return patterns
    
    return patterns


def calculate_momentum(candles, period=5):
    """
    Calcula el momentum del precio
    
    Args:
        candles: Lista de velas
        period: Período para calcular momentum
    
    Returns:
        dict con momentum y señal
    """
    if not candles or len(candles) < period + 1:
        return {"momentum": 0, "signal": "NEUTRAL"}
    
    # Precio actual vs precio hace N períodos
    current_close = candles[0]["close"]
    past_close = candles[period]["close"]
    
    momentum = ((current_close - past_close) / past_close) * 100
    
    signal = "NEUTRAL"
    if momentum > 0.5:
        signal = "STRONG_BULLISH"
    elif momentum > 0.1:
        signal = "BULLISH"
    elif momentum < -0.5:
        signal = "STRONG_BEARISH"
    elif momentum < -0.1:
        signal = "BEARISH"
    
    return {
        "momentum": round(momentum, 4),
        "signal": signal
    }


def detect_divergence(candles, indicators, lookback=10):
    """
    Detecta divergencias entre precio e indicadores (RSI/MACD)
    
    Args:
        candles: Lista de velas
        indicators: Dict con valores de indicadores actuales
        lookback: Velas a analizar
    
    Returns:
        dict con tipo de divergencia detectada
    """
    if not candles or len(candles) < lookback:
        return {"divergence": "NONE", "type": None}
    
    recent_candles = candles[:lookback]
    
    # Obtener máximos y mínimos de precio
    prices = [c["close"] for c in recent_candles]
    price_max = max(prices)
    price_min = min(prices)
    
    current_price = candles[0]["close"]
    rsi = indicators.get("rsi", 50)
    
    # Divergencia bajista: Precio hace máximos más altos pero RSI hace máximos más bajos
    if current_price >= price_max * 0.99 and rsi < 60:
        return {
            "divergence": "BEARISH",
            "type": "REGULAR",
            "strength": 0.7
        }
    
    # Divergencia alcista: Precio hace mínimos más bajos pero RSI hace mínimos más altos
    if current_price <= price_min * 1.01 and rsi > 40:
        return {
            "divergence": "BULLISH",
            "type": "REGULAR",
            "strength": 0.7
        }
    
    return {"divergence": "NONE", "type": None}


def calculate_volume_profile(candles, bins=10):
    """
    Calcula el perfil de volumen para identificar zonas de alto interés
    
    Args:
        candles: Lista de velas
        bins: Número de niveles de precio a analizar
    
    Returns:
        dict con niveles de alto volumen
    """
    if not candles or len(candles) < 20:
        return {"high_volume_zones": [], "poc": None}  # POC = Point of Control
    
    # Extraer precios y volúmenes
    prices = []
    volumes = []
    
    for c in candles:
        # Usar precio promedio de la vela
        avg_price = (c["high"] + c["low"]) / 2
        prices.append(avg_price)
        volumes.append(c.get("volume", 0))
    
    if not volumes or sum(volumes) == 0:
        return {"high_volume_zones": [], "poc": None}
    
    # Encontrar rango de precios
    price_min = min(prices)
    price_max = max(prices)
    price_range = price_max - price_min
    
    if price_range == 0:
        return {"high_volume_zones": [], "poc": None}
    
    # Crear bins de precio
    bin_size = price_range / bins
    volume_by_bin = {}
    
    for price, volume in zip(prices, volumes):
        bin_index = int((price - price_min) / bin_size)
        if bin_index >= bins:
            bin_index = bins - 1
        
        if bin_index not in volume_by_bin:
            volume_by_bin[bin_index] = 0
        volume_by_bin[bin_index] += volume
    
    # Encontrar POC (nivel con mayor volumen)
    if volume_by_bin:
        poc_bin = max(volume_by_bin, key=volume_by_bin.get)
        poc_price = price_min + (poc_bin * bin_size) + (bin_size / 2)
    else:
        poc_price = None
    
    # Identificar zonas de alto volumen (top 30%)
    avg_volume = sum(volume_by_bin.values()) / len(volume_by_bin)
    high_volume_zones = []
    
    for bin_idx, vol in volume_by_bin.items():
        if vol > avg_volume * 1.3:
            zone_price = price_min + (bin_idx * bin_size) + (bin_size / 2)
            high_volume_zones.append(zone_price)
    
    return {
        "high_volume_zones": high_volume_zones,
        "poc": poc_price
    }


def analyze_price_action(candles):
    """
    Análisis completo de price action combinando múltiples técnicas
    
    Args:
        candles: Lista de velas
    
    Returns:
        dict con análisis completo
    """
    analysis = {
        "support_resistance": calculate_support_resistance(candles),
        "candlestick_pattern": detect_candlestick_patterns(candles),
        "momentum": calculate_momentum(candles),
        "volume_profile": calculate_volume_profile(candles)
    }
    
    return analysis
