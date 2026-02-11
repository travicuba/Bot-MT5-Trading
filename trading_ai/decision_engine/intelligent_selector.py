# decision_engine/intelligent_selector.py
"""
Selector Inteligente de Estrategias

Integra Machine Learning para elegir la mejor estrategia
"""

import sys
import os

# Importar librerías de estrategias
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from decision_engine.strategy_library import get_all_strategies
except:
    # Fallback si no existe
    def get_all_strategies():
        return [
            {"name": "MEAN_REVERSION", "type": "REVERSAL", "best_conditions": {}, "avoid_conditions": {}},
            {"name": "TREND_FOLLOWING", "type": "TREND", "best_conditions": {}, "avoid_conditions": {}},
            {"name": "TREND_PULLBACK", "type": "PULLBACK", "best_conditions": {}, "avoid_conditions": {}}
        ]

try:
    from ml_adaptive_system import get_ml_strategy_priority
    ML_AVAILABLE = True
except:
    ML_AVAILABLE = False
    print("⚠️ Sistema ML no disponible, usando selector básico")


def score_strategy(strategy, context, ml_priority=1.0):
    """
    Calcula score de una estrategia considerando:
    1. Compatibilidad con contexto (70%)
    2. Prioridad ML (30%)
    """
    
    # Parte 1: Compatibilidad con contexto
    context_score = 0.0
    max_points = 0
    earned_points = 0
    
    best_conditions = strategy.get("best_conditions", {})
    avoid_conditions = strategy.get("avoid_conditions", {})
    
    # Evaluar best_conditions
    for condition_key, desired_values in best_conditions.items():
        max_points += 1
        current_value = context.get(condition_key)
        
        if current_value in desired_values:
            earned_points += 1
    
    # Penalizar avoid_conditions
    penalty = 0
    for condition_key, avoided_values in avoid_conditions.items():
        current_value = context.get(condition_key)
        
        if current_value in avoided_values:
            penalty += 0.25
    
    # Score de contexto (0-1)
    if max_points > 0:
        context_score = (earned_points / max_points) - penalty
        context_score = max(0, min(1, context_score))
    else:
        context_score = 0.5  # Neutral si no hay condiciones
    
    # Parte 2: Integrar prioridad ML
    # Context score tiene 70% peso, ML priority tiene 30%
    final_score = (context_score * 0.70) + ((ml_priority / 2.0) * 0.30)
    
    return final_score


def select_intelligent_strategy(context):
    """
    Selecciona la mejor estrategia usando ML
    
    Args:
        context: Contexto actual del mercado
    
    Returns:
        dict: {
            "name": str,
            "type": str,
            "score": float,
            "ml_priority": float,
            "reason": str
        }
    """
    
    strategies = get_all_strategies()
    
    if not strategies:
        print("⚠️ No hay estrategias disponibles")
        return None
    
    # Calcular scores con ML
    scored_strategies = []
    
    for strategy in strategies:
        strategy_name = strategy["name"]
        
        # Obtener prioridad ML si está disponible
        ml_priority = 1.0
        if ML_AVAILABLE:
            try:
                ml_priority = get_ml_strategy_priority(strategy_name, context)
            except:
                ml_priority = 1.0
        
        # Calcular score final
        score = score_strategy(strategy, context, ml_priority)
        
        scored_strategies.append({
            "name": strategy_name,
            "type": strategy["type"],
            "description": strategy.get("description", ""),
            "score": score,
            "ml_priority": ml_priority,
            "context_fit": score / ml_priority if ml_priority > 0 else score
        })
    
    # Ordenar por score
    scored_strategies.sort(key=lambda x: x["score"], reverse=True)
    
    # Mostrar top 3
    print("\n📊 TOP 3 ESTRATEGIAS:")
    for i, s in enumerate(scored_strategies[:3], 1):
        ml_tag = f" [ML: {s['ml_priority']:.2f}x]" if ML_AVAILABLE else ""
        print(f"   {i}. {s['name']}: {s['score']:.2f}{ml_tag}")
    
    # Seleccionar la mejor
    best = scored_strategies[0]
    
    # Umbral mínimo
    MIN_SCORE = 0.30  # Más permisivo para testing
    
    if best["score"] < MIN_SCORE:
        print(f"❌ Mejor estrategia ({best['name']}) tiene score muy bajo ({best['score']:.2f})")
        return None
    
    # Construir reason
    reason_parts = []
    if ML_AVAILABLE and best["ml_priority"] > 1.2:
        reason_parts.append(f"ML recomienda (priority: {best['ml_priority']:.2f}x)")
    if best["context_fit"] > 0.7:
        reason_parts.append("Excelente fit con contexto")
    elif best["context_fit"] > 0.5:
        reason_parts.append("Buen fit con contexto")
    
    best["reason"] = ", ".join(reason_parts) if reason_parts else "Mejor opción disponible"
    
    print(f"✅ Estrategia seleccionada: {best['name']} (score: {best['score']:.2f})")
    if reason_parts:
        print(f"   Razón: {best['reason']}")
    
    return best


# Para compatibilidad con código existente
def select_setup(context):
    """Wrapper para compatibilidad con código existente"""
    return select_intelligent_strategy(context)


if __name__ == "__main__":
    # Test
    test_context = {
        "trend": "SIDEWAYS",
        "volatility": "NORMAL",
        "market_regime": "RANGING",
        "rsi_state": "NEUTRAL",
        "macd_state": "NEUTRAL",
        "bb_position": "MIDDLE",
        "confidence": 0.40,
        "trade_allowed": True
    }
    
    result = select_intelligent_strategy(test_context)
    print("\nResultado:")
    if result:
        print(f"  Estrategia: {result['name']}")
        print(f"  Score: {result['score']:.2f}")
        print(f"  ML Priority: {result['ml_priority']:.2f}")
        print(f"  Razón: {result['reason']}")
