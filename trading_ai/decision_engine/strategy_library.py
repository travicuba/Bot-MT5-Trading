# decision_engine/strategy_library.py
"""
Librería de Estrategias de Trading

8 estrategias diferentes para que el ML elija la mejor según contexto
"""


def get_all_strategies():
    """
    Retorna todas las estrategias disponibles con sus condiciones
    
    El ML aprenderá cuál funciona mejor en cada contexto
    """
    return [
        {
            "name": "MEAN_REVERSION",
            "type": "REVERSAL",
            "description": "Reversión desde extremos",
            "best_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["NORMAL", "LOW"],
                "market_regime": ["RANGING", "QUIET"],
                "rsi_state": ["OVERBOUGHT", "OVERSOLD"]
            },
            "avoid_conditions": {
                "trend": ["STRONG_UP", "STRONG_DOWN"],
                "market_regime": ["TRENDING_VOLATILE"]
            }
        },
        
        {
            "name": "TREND_FOLLOWING",
            "type": "TREND",
            "description": "Seguir tendencias fuertes",
            "best_conditions": {
                "trend": ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"],
                "volatility": ["NORMAL", "HIGH"],
                "market_regime": ["TRENDING", "TRENDING_VOLATILE"]
            },
            "avoid_conditions": {
                "trend": ["SIDEWAYS"],
                "market_regime": ["CHOPPY", "QUIET"]
            }
        },
        
        {
            "name": "TREND_PULLBACK",
            "type": "PULLBACK",
            "description": "Entrar en pullbacks de tendencia",
            "best_conditions": {
                "trend": ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"],
                "volatility": ["NORMAL"],
                "market_regime": ["TRENDING"]
            },
            "avoid_conditions": {
                "market_regime": ["CHOPPY", "QUIET"],
                "volatility": ["HIGH"]
            }
        },
        
        {
            "name": "BREAKOUT",
            "type": "BREAKOUT",
            "description": "Romper rangos consolidados",
            "best_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["LOW", "NORMAL"],
                "market_regime": ["RANGING", "QUIET"],
                "bb_position": ["NEAR_UPPER", "NEAR_LOWER"]
            },
            "avoid_conditions": {
                "volatility": ["HIGH"],
                "market_regime": ["CHOPPY"]
            }
        },
        
        {
            "name": "MOMENTUM",
            "type": "MOMENTUM",
            "description": "Capturar momentum fuerte",
            "best_conditions": {
                "trend": ["STRONG_UP", "STRONG_DOWN"],
                "volatility": ["HIGH"],
                "market_regime": ["TRENDING_VOLATILE"],
                "macd_state": ["STRONG_BULLISH", "STRONG_BEARISH"]
            },
            "avoid_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["LOW"]
            }
        },
        
        {
            "name": "SCALPING",
            "type": "SCALP",
            "description": "Trades rápidos en rangos",
            "best_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["NORMAL", "HIGH"],
                "market_regime": ["RANGING", "CHOPPY"]
            },
            "avoid_conditions": {
                "trend": ["STRONG_UP", "STRONG_DOWN"],
                "volatility": ["LOW"]
            }
        },
        
        {
            "name": "RANGE_TRADING",
            "type": "RANGE",
            "description": "Operar dentro de rangos",
            "best_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["LOW", "NORMAL"],
                "market_regime": ["RANGING", "QUIET"],
                "bb_position": ["UPPER_HALF", "LOWER_HALF"]
            },
            "avoid_conditions": {
                "trend": ["STRONG_UP", "STRONG_DOWN"],
                "volatility": ["HIGH"]
            }
        },
        
        {
            "name": "VOLATILITY_BREAKOUT",
            "type": "VOLATILITY",
            "description": "Aprovechar aumentos de volatilidad",
            "best_conditions": {
                "volatility": ["HIGH"],
                "market_regime": ["TRENDING_VOLATILE", "CHOPPY"]
            },
            "avoid_conditions": {
                "volatility": ["LOW"],
                "market_regime": ["QUIET"]
            }
        }
    ]
