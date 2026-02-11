import json
import os
from collections import defaultdict

STATS_FILE = "learning_data/setup_stats.json"


def load_stats():
    if not os.path.exists(STATS_FILE):
        return defaultdict(lambda: {"wins": 0, "losses": 0})

    with open(STATS_FILE, "r") as f:
        return defaultdict(lambda: {"wins": 0, "losses": 0}, json.load(f))


def save_stats(stats):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


def update_learning(trade_result):
    """
    trade_result viene directamente de MT5
    """
    stats = load_stats()
    setup = trade_result["setup"]

    if trade_result["result"] == "WIN":
        stats[setup]["wins"] += 1
    else:
        stats[setup]["losses"] += 1

    save_stats(stats)
    return stats