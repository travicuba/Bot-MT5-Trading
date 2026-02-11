# decision_engine/setup_selector.py

"""
Selector mejorado de estrategias (setups) que:
1. Evalúa qué setup es mejor para el contexto actual
2. Usa estadísticas de performance histórica (learning)
3. Se adapta dinámicamente
"""

import os
import json


# ========== DEFINICIÓN DE SETUPS DISPONIBLES ==========

def get_available_setups():
    """
    Define TODOS los setups que el sistema conoce.
    Cada setup tiene condiciones específicas de activación.
    """
    return [
        {
            "name": "TREND_FOLLOWING",
            "type": "TREND",
            "description": "Operar a favor de tendencias fuertes",
            "best_conditions": {
                "trend": ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"],
                "volatility": ["NORMAL", "HIGH"],
                "market_regime": ["TRENDING", "TRENDING_VOLATILE"]
            },
            "avoid_conditions": {
                "market_regime": ["CHOPPY", "QUIET"],
                "rsi_state": ["OVERBOUGHT", "OVERSOLD"]
            }
        },
        {
            "name": "MEAN_REVERSION",
            "type": "REVERSAL",
            "description": "Operar reversiones desde zonas extremas",
            "best_conditions": {
                "trend": ["SIDEWAYS"],
                "volatility": ["NORMAL", "LOW"],
                "market_regime": ["RANGING", "QUIET"],
                "rsi_state": ["OVERBOUGHT", "OVERSOLD"],
                "bb_position": ["NEAR_UPPER", "NEAR_LOWER"]
            },
            "avoid_conditions": {
                "trend": ["STRONG_UP", "STRONG_DOWN"],
                "market_regime": ["TRENDING_VOLATILE", "CHOPPY"]
            }
        },
        {
            "name": "TREND_PULLBACK",
            "type": "PULLBACK",
            "description": "Entrar en pullbacks de tendencias fuertes",
            "best_conditions": {
                "trend": ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"],
                "volatility": ["NORMAL"],
                "market_regime": ["TRENDING"],
                "bb_position": ["MIDDLE", "LOWER_HALF", "UPPER_HALF"]
            },
            "avoid_conditions": {
                "market_regime": ["CHOPPY", "QUIET"],
                "volatility": ["HIGH"]
            }
        }
    ]


# ========== SCORING DE SETUPS ==========

def score_setup(setup, context, learning_stats=None):
    """
    Calcula un score para un setup específico basado en:
    1. Compatibilidad con contexto actual (70% peso)
    2. Performance histórica (30% peso)
    
    Args:
        setup: Diccionario con definición del setup
        context: Contexto actual del mercado
        learning_stats: Estadísticas de performance (opcional)
    
    Returns:
        float: Score entre 0 y 1
    """
    
    score = 0.0
    
    # ========== PARTE 1: COMPATIBILIDAD CON CONTEXTO (70%) ==========
    
    context_score = 0.0
    max_context_points = 0
    earned_context_points = 0
    
    best_conditions = setup.get("best_conditions", {})
    avoid_conditions = setup.get("avoid_conditions", {})
    
    # Revisar best_conditions
    for condition_key, desired_values in best_conditions.items():
        max_context_points += 1
        current_value = context.get(condition_key)
        
        if current_value in desired_values:
            earned_context_points += 1
    
    # Penalizar avoid_conditions
    penalty = 0
    for condition_key, avoided_values in avoid_conditions.items():
        current_value = context.get(condition_key)
        
        if current_value in avoided_values:
            penalty += 0.3  # Penalización fuerte
    
    # Calcular score de contexto
    if max_context_points > 0:
        context_score = (earned_context_points / max_context_points) - penalty
        context_score = max(0, min(1, context_score))  # Clamp entre 0 y 1
    
    # ========== PARTE 2: PERFORMANCE HISTÓRICA (30%) ==========
    
    performance_score = 0.5  # Default neutral
    
    if learning_stats and setup["name"] in learning_stats:
        stats = learning_stats[setup["name"]]
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total = wins + losses
        
        if total >= 10:  # Mínimo 10 trades para considerar estadísticas
            win_rate = wins / total
            
            # Convertir win rate a score (0.5 = neutral, 1.0 = perfecto, 0.0 = terrible)
            if win_rate >= 0.6:
                performance_score = 0.5 + (win_rate - 0.6) * 1.25  # 60%+ es bueno
            elif win_rate >= 0.5:
                performance_score = 0.5
            else:
                performance_score = win_rate  # Penalizar win rates bajos
        
        elif total >= 5:  # Entre 5 y 10 trades: pesar menos
            win_rate = wins / total
            performance_score = 0.5 + (win_rate - 0.5) * 0.5  # Menos impacto
    
    # ========== SCORE FINAL ==========
    
    final_score = (context_score * 0.70) + (performance_score * 0.30)
    
    return final_score


# ========== SELECTOR PRINCIPAL ==========

def select_setup(context):
    """
    Decide qué setup usar según el contexto y el scoring dinámico.
    Puede devolver None si NO hay setup válido.
    
    VERSIÓN MEJORADA: Usa learning stats
    """
    
    # Obtener setups disponibles
    setups = get_available_setups()
    
    if not setups:
        print("⚠️ No hay setups disponibles")
        return None
    
    # Cargar estadísticas de aprendizaje
    learning_stats = _load_learning_stats()
    
    # Calcular scores para cada setup
    scored_setups = []
    
    for setup in setups:
        score = score_setup(setup, context, learning_stats)
        
        scored_setups.append({
            "name": setup["name"],
            "type": setup["type"],
            "description": setup["description"],
            "score": score
        })
    
    # Ordenar por score descendente
    scored_setups.sort(key=lambda x: x["score"], reverse=True)
    
    # Mostrar scores
    print("\n📊 SCORES DE SETUPS:")
    for s in scored_setups:
        print(f"   {s['name']}: {s['score']:.2f}")
    
    # Seleccionar el mejor
    best = scored_setups[0]
    
    # Umbral mínimo de calidad
    MIN_SCORE = 0.50
    
    if best["score"] < MIN_SCORE:
        print(f"❌ Mejor setup ({best['name']}) tiene score muy bajo ({best['score']:.2f})")
        return None
    
    print(f"✅ Setup seleccionado: {best['name']} (score: {best['score']:.2f})")
    
    return best


# ========== HELPERS ==========

def _load_learning_stats():
    """Carga estadísticas de aprendizaje desde archivo JSON"""
    
    stats_file = "learning_data/setup_stats.json"
    
    if not os.path.exists(stats_file):
        return {}
    
    try:
        with open(stats_file, "r") as f:
            stats = json.load(f)
        
        print(f"📚 Learning stats cargadas: {len(stats)} setups con historial")
        return stats
        
    except Exception as e:
        print(f"⚠️ Error cargando learning stats: {e}")
        return {}


# ========== FUNCIÓN PARA TESTING ==========

def test_selector():
    """Función de prueba para verificar el selector"""
    
    # Contexto de prueba: Tendencia alcista fuerte
    test_context = {
        "trend": "STRONG_UP",
        "volatility": "NORMAL",
        "market_regime": "TRENDING",
        "rsi_state": "NEUTRAL",
        "macd_state": "STRONG_BULLISH",
        "bb_position": "MIDDLE",
        "confidence": 0.85,
        "trade_allowed": True
    }
    
    print("🧪 TESTING SETUP SELECTOR")
    print("=" * 50)
    print("Contexto de prueba:")
    for k, v in test_context.items():
        print(f"  {k}: {v}")
    print("=" * 50)
    
    result = select_setup(test_context)
    
    if result:
        print(f"\n✅ Resultado: {result['name']}")
        print(f"   Score: {result['score']:.2f}")
        print(f"   Descripción: {result['description']}")
    else:
        print("\n❌ No se seleccionó ningún setup")


if __name__ == "__main__":
    test_selector()
