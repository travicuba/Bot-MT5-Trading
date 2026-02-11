# ml_analysis/ml_analyzer.py

"""
Módulo de Análisis de Machine Learning

Analiza el aprendizaje del bot y genera métricas e insights.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict


class MLAnalyzer:
    """Analizador de Machine Learning del bot"""
    
    def __init__(self):
        self.stats_file = "learning_data/setup_stats.json"
        self.history_file = "learning_data/trade_history.json"
        self.processed_file = "learning_data/processed_signals.txt"
        
        # Datos cargados
        self.stats = {}
        self.history = []
        self.processed_signals = []
        
        # Análisis
        self.analysis = {}
    
    def load_data(self):
        """Cargar datos de aprendizaje"""
        # Cargar stats
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)
        
        # Cargar historial
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                self.history = json.load(f)
        
        # Cargar señales procesadas
        if os.path.exists(self.processed_file):
            with open(self.processed_file, "r") as f:
                self.processed_signals = f.read().splitlines()
        
        return len(self.history) > 0
    
    def analyze(self):
        """Realizar análisis completo"""
        if not self.load_data():
            return None
        
        self.analysis = {
            "learning_progress": self.analyze_learning_progress(),
            "feature_importance": self.analyze_feature_importance(),
            "prediction_accuracy": self.analyze_prediction_accuracy(),
            "setup_evolution": self.analyze_setup_evolution(),
            "confidence_calibration": self.analyze_confidence_calibration(),
            "recommendations": self.generate_recommendations()
        }
        
        return self.analysis
    
    def analyze_learning_progress(self):
        """Analizar progreso del aprendizaje con el tiempo"""
        if not self.history:
            return None
        
        # Dividir en ventanas temporales
        window_size = 10  # Analizar cada 10 trades
        
        windows = []
        for i in range(0, len(self.history), window_size):
            window = self.history[i:i+window_size]
            
            if len(window) < 3:  # Mínimo 3 trades por ventana
                continue
            
            wins = sum(1 for t in window if t.get("result") == "WIN")
            total = len(window)
            win_rate = (wins / total) * 100 if total > 0 else 0
            
            avg_pips = sum(t.get("pips", 0) for t in window) / total if total > 0 else 0
            
            # Fecha promedio de la ventana
            timestamps = [t.get("timestamp", "") for t in window if t.get("timestamp")]
            avg_timestamp = timestamps[len(timestamps)//2] if timestamps else ""
            
            windows.append({
                "window_num": i // window_size + 1,
                "timestamp": avg_timestamp,
                "win_rate": win_rate,
                "avg_pips": avg_pips,
                "total_trades": total
            })
        
        # Calcular tendencia
        if len(windows) >= 2:
            first_half_wr = sum(w["win_rate"] for w in windows[:len(windows)//2]) / (len(windows)//2)
            second_half_wr = sum(w["win_rate"] for w in windows[len(windows)//2:]) / (len(windows) - len(windows)//2)
            
            improvement = second_half_wr - first_half_wr
            
            trend = "improving" if improvement > 5 else "stable" if improvement > -5 else "declining"
        else:
            trend = "insufficient_data"
        
        return {
            "windows": windows,
            "trend": trend,
            "total_windows": len(windows)
        }
    
    def analyze_feature_importance(self):
        """Analizar qué features (indicadores) son más importantes"""
        if not self.history:
            return None
        
        # Analizar correlación entre indicadores y resultados
        features = {
            "trend": {"wins": 0, "losses": 0, "importance": 0},
            "rsi": {"wins": 0, "losses": 0, "importance": 0},
            "macd": {"wins": 0, "losses": 0, "importance": 0},
            "volatility": {"wins": 0, "losses": 0, "importance": 0}
        }
        
        # Por simplicidad, usar setup como proxy de features
        # En producción, esto requeriría análisis más profundo
        
        for setup_name, data in self.stats.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            total = wins + losses
            
            if total == 0:
                continue
            
            win_rate = wins / total
            
            # Mapear setup a features dominantes
            if "TREND" in setup_name:
                features["trend"]["wins"] += wins
                features["trend"]["losses"] += losses
            
            if "MEAN" in setup_name or "REVERSION" in setup_name:
                features["rsi"]["wins"] += wins
                features["rsi"]["losses"] += losses
            
            if "BREAKOUT" in setup_name:
                features["volatility"]["wins"] += wins
                features["volatility"]["losses"] += losses
        
        # Calcular importancia
        for feature, data in features.items():
            total = data["wins"] + data["losses"]
            if total > 0:
                wr = data["wins"] / total
                # Importancia = win_rate * frecuencia_uso
                data["importance"] = wr * (total / len(self.history))
        
        # Ordenar por importancia
        sorted_features = sorted(features.items(), key=lambda x: x[1]["importance"], reverse=True)
        
        return {
            "features": features,
            "ranked": [{"name": name, **data} for name, data in sorted_features]
        }
    
    def analyze_prediction_accuracy(self):
        """Analizar accuracy de las predicciones del bot"""
        if not self.history:
            return None
        
        # Matriz de confusión simplificada
        # Predicción: Alta confianza = WIN esperado, Baja confianza = incierto
        
        high_conf_wins = 0
        high_conf_losses = 0
        low_conf_wins = 0
        low_conf_losses = 0
        
        confidence_threshold = 0.8
        
        for trade in self.history:
            # En el historial no tenemos confidence, usar proxy
            # Si fue un WIN, asumimos que el bot tenía "confianza"
            result = trade.get("result", "")
            
            # Simplificación: analizar por setup performance
            setup = trade.get("setup", "")
            setup_stats = self.stats.get(setup, {})
            
            total_trades = setup_stats.get("wins", 0) + setup_stats.get("losses", 0)
            if total_trades > 0:
                setup_wr = setup_stats.get("wins", 0) / total_trades
                high_confidence = setup_wr > confidence_threshold
            else:
                high_confidence = False
            
            if result == "WIN":
                if high_confidence:
                    high_conf_wins += 1
                else:
                    low_conf_wins += 1
            else:
                if high_confidence:
                    high_conf_losses += 1
                else:
                    low_conf_losses += 1
        
        # Calcular accuracy
        total_high_conf = high_conf_wins + high_conf_losses
        total_low_conf = low_conf_wins + low_conf_losses
        
        high_conf_accuracy = (high_conf_wins / total_high_conf * 100) if total_high_conf > 0 else 0
        low_conf_accuracy = (low_conf_wins / total_low_conf * 100) if total_low_conf > 0 else 0
        
        overall_accuracy = ((high_conf_wins + low_conf_wins) / len(self.history) * 100) if self.history else 0
        
        return {
            "overall_accuracy": overall_accuracy,
            "high_confidence_accuracy": high_conf_accuracy,
            "low_confidence_accuracy": low_conf_accuracy,
            "confusion_matrix": {
                "high_conf_wins": high_conf_wins,
                "high_conf_losses": high_conf_losses,
                "low_conf_wins": low_conf_wins,
                "low_conf_losses": low_conf_losses
            }
        }
    
    def analyze_setup_evolution(self):
        """Analizar evolución de cada setup con el tiempo"""
        if not self.history:
            return None
        
        # Agrupar trades por setup y por tiempo
        setup_evolution = defaultdict(list)
        
        window_size = 5
        
        for setup_name in self.stats.keys():
            setup_trades = [t for t in self.history if t.get("setup") == setup_name]
            
            # Dividir en ventanas
            for i in range(0, len(setup_trades), window_size):
                window = setup_trades[i:i+window_size]
                
                if len(window) < 2:
                    continue
                
                wins = sum(1 for t in window if t.get("result") == "WIN")
                win_rate = (wins / len(window)) * 100
                
                setup_evolution[setup_name].append({
                    "window": i // window_size + 1,
                    "win_rate": win_rate,
                    "trades": len(window)
                })
        
        return dict(setup_evolution)
    
    def analyze_confidence_calibration(self):
        """
        Analizar si la confianza del bot está bien calibrada
        (i.e., cuando dice 80% confianza, realmente acierta ~80% de las veces)
        """
        # Por ahora simplificado, en el futuro se puede mejorar
        # cuando tengamos confidence guardado en el historial
        
        if not self.stats:
            return None
        
        calibration = []
        
        for setup_name, data in self.stats.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            total = wins + losses
            
            if total < 5:  # Mínimo 5 trades
                continue
            
            actual_win_rate = (wins / total) * 100
            
            # En el futuro, comparar con confidence promedio del setup
            # Por ahora, solo reportar accuracy real
            
            calibration.append({
                "setup": setup_name,
                "actual_win_rate": actual_win_rate,
                "total_trades": total
            })
        
        return calibration
    
    def generate_recommendations(self):
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []
        
        if not self.stats or not self.history:
            return ["Necesitas más datos de trading para generar recomendaciones"]
        
        # Analizar setups
        for setup_name, data in self.stats.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            total = wins + losses
            
            if total < 10:  # Mínimo 10 trades
                continue
            
            win_rate = (wins / total) * 100
            avg_pips = data.get("total_pips", 0) / total if total > 0 else 0
            
            # Recomendaciones específicas
            if win_rate < 40:
                recommendations.append({
                    "type": "warning",
                    "setup": setup_name,
                    "message": f"{setup_name}: Win rate bajo ({win_rate:.1f}%). Considera desactivar esta estrategia."
                })
            
            elif win_rate > 60 and total >= 20:
                recommendations.append({
                    "type": "success",
                    "setup": setup_name,
                    "message": f"{setup_name}: Excelente performance ({win_rate:.1f}% WR). Considera aumentar tamaño de posición."
                })
            
            if avg_pips < -1 and total >= 15:
                recommendations.append({
                    "type": "warning",
                    "setup": setup_name,
                    "message": f"{setup_name}: Pips negativos ({avg_pips:.2f}). Revisar SL/TP."
                })
        
        # Análisis general
        total_trades = len(self.history)
        total_wins = sum(1 for t in self.history if t.get("result") == "WIN")
        overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        if overall_wr < 45 and total_trades >= 30:
            recommendations.append({
                "type": "critical",
                "setup": "GENERAL",
                "message": f"Win rate general bajo ({overall_wr:.1f}%). Revisar configuración global del bot."
            })
        
        elif overall_wr > 55 and total_trades >= 50:
            recommendations.append({
                "type": "success",
                "setup": "GENERAL",
                "message": f"¡Excelente! Win rate {overall_wr:.1f}%. El bot está aprendiendo correctamente."
            })
        
        if total_trades < 20:
            recommendations.append({
                "type": "info",
                "setup": "GENERAL",
                "message": f"Solo {total_trades} trades registrados. Necesitas al menos 50 para análisis confiable."
            })
        
        return recommendations
    
    def get_summary(self):
        """Obtener resumen del análisis"""
        if not self.analysis:
            self.analyze()
        
        total_trades = len(self.history)
        total_setups = len(self.stats)
        
        # Setup más exitoso
        best_setup = None
        best_wr = 0
        
        for setup_name, data in self.stats.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            total = wins + losses
            
            if total >= 5:  # Mínimo 5 trades
                wr = (wins / total) * 100
                if wr > best_wr:
                    best_wr = wr
                    best_setup = setup_name
        
        # Tendencia de aprendizaje
        progress = self.analysis.get("learning_progress", {})
        trend = progress.get("trend", "unknown") if progress else "unknown"
        
        return {
            "total_trades": total_trades,
            "total_setups": total_setups,
            "best_setup": best_setup,
            "best_setup_wr": best_wr,
            "learning_trend": trend,
            "processed_signals": len(self.processed_signals)
        }


# Testing
if __name__ == "__main__":
    print("🧪 Testing ML Analyzer...")
    
    analyzer = MLAnalyzer()
    
    if analyzer.load_data():
        print(f"✅ Datos cargados: {len(analyzer.history)} trades")
        
        analysis = analyzer.analyze()
        
        if analysis:
            print("\n📊 ANÁLISIS COMPLETO:")
            
            # Learning Progress
            progress = analysis.get("learning_progress")
            if progress:
                print(f"\nProgreso de Aprendizaje:")
                print(f"  Ventanas analizadas: {progress['total_windows']}")
                print(f"  Tendencia: {progress['trend']}")
            
            # Feature Importance
            features = analysis.get("feature_importance")
            if features:
                print(f"\nImportancia de Features:")
                for feature in features['ranked'][:3]:
                    print(f"  {feature['name']}: {feature['importance']:.3f}")
            
            # Recommendations
            recs = analysis.get("recommendations", [])
            print(f"\n💡 Recomendaciones ({len(recs)}):")
            for rec in recs[:5]:
                print(f"  [{rec['type']}] {rec['message']}")
        
        # Summary
        summary = analyzer.get_summary()
        print(f"\n📋 RESUMEN:")
        print(f"  Total Trades: {summary['total_trades']}")
        print(f"  Mejor Setup: {summary['best_setup']} ({summary['best_setup_wr']:.1f}% WR)")
        print(f"  Tendencia: {summary['learning_trend']}")
    
    else:
        print("⚠️ No hay datos suficientes para analizar")