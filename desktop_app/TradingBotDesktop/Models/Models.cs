using System.Text.Json.Serialization;

namespace TradingBotDesktop.Models;

// =====================
// BOT STATUS
// =====================
public class BotStatus
{
    [JsonPropertyName("running")]       public bool   Running      { get; set; }
    [JsonPropertyName("uptime_seconds")] public int   UptimeSeconds { get; set; }
    [JsonPropertyName("pid")]           public int?   Pid           { get; set; }
    [JsonPropertyName("active_trades")] public int   ActiveTrades  { get; set; }
    [JsonPropertyName("timestamp")]     public string Timestamp     { get; set; } = "";

    public string UptimeFormatted =>
        UptimeSeconds < 60  ? $"{UptimeSeconds}s" :
        UptimeSeconds < 3600 ? $"{UptimeSeconds / 60}m {UptimeSeconds % 60}s" :
        $"{UptimeSeconds / 3600}h {(UptimeSeconds % 3600) / 60}m";
}

// =====================
// BOT CONFIG
// =====================
public class BotConfig
{
    [JsonPropertyName("min_confidence")]       public int    MinConfidence      { get; set; } = 35;
    [JsonPropertyName("cooldown")]             public int    Cooldown           { get; set; } = 30;
    [JsonPropertyName("max_daily_trades")]     public int    MaxDailyTrades     { get; set; } = 50;
    [JsonPropertyName("max_losses")]           public int    MaxLosses          { get; set; } = 5;
    [JsonPropertyName("lot_size")]             public double LotSize            { get; set; } = 0.01;
    [JsonPropertyName("start_hour")]           public string StartHour          { get; set; } = "00:00";
    [JsonPropertyName("end_hour")]             public string EndHour            { get; set; } = "23:59";
    [JsonPropertyName("max_concurrent_trades")] public int  MaxConcurrentTrades { get; set; } = 3;
    [JsonPropertyName("min_signal_interval")]  public int   MinSignalInterval   { get; set; } = 60;
    [JsonPropertyName("avoid_repeat_strategy")] public bool AvoidRepeatStrategy { get; set; } = true;
    [JsonPropertyName("auto_optimize")]        public bool   AutoOptimize        { get; set; } = true;
}

// =====================
// STATS
// =====================
public class PeriodStats
{
    [JsonPropertyName("trades")] public int    Trades { get; set; }
    [JsonPropertyName("wins")]   public int    Wins   { get; set; }
    [JsonPropertyName("pips")]   public double Pips   { get; set; }

    public double WinRate => Trades > 0 ? (Wins / (double)Trades) * 100 : 0;
}

public class BotStats
{
    [JsonPropertyName("total_trades")] public int        TotalTrades { get; set; }
    [JsonPropertyName("wins")]         public int        Wins        { get; set; }
    [JsonPropertyName("losses")]       public int        Losses      { get; set; }
    [JsonPropertyName("win_rate")]     public double     WinRate     { get; set; }
    [JsonPropertyName("total_pips")]   public double     TotalPips   { get; set; }
    [JsonPropertyName("today")]        public PeriodStats Today      { get; set; } = new();
    [JsonPropertyName("week")]         public PeriodStats Week       { get; set; } = new();
    [JsonPropertyName("setup_stats")]  public Dictionary<string, SetupStatEntry>? SetupStats { get; set; }
}

public class SetupStatEntry
{
    [JsonPropertyName("total")]  public int    Total  { get; set; }
    [JsonPropertyName("wins")]   public int    Wins   { get; set; }
    [JsonPropertyName("losses")] public int    Losses { get; set; }
    [JsonPropertyName("pips")]   public double Pips   { get; set; }
}

// =====================
// HISTORIAL DE TRADES
// =====================
public class TradeRecord
{
    [JsonPropertyName("signal_id")]  public string SignalId   { get; set; } = "";
    [JsonPropertyName("result")]     public string Result     { get; set; } = "";
    [JsonPropertyName("pips")]       public double Pips       { get; set; }
    [JsonPropertyName("timestamp")]  public string Timestamp  { get; set; } = "";
    [JsonPropertyName("setup_name")] public string SetupName  { get; set; } = "";
    [JsonPropertyName("action")]     public string Action     { get; set; } = "";
    [JsonPropertyName("symbol")]     public string Symbol     { get; set; } = "";

    public string ResultDisplay => Result switch {
        "WIN"  => "GANADA",
        "LOSS" => "PERDIDA",
        _      => Result,
    };
}

public class HistoryResponse
{
    [JsonPropertyName("trades")] public List<TradeRecord> Trades { get; set; } = new();
    [JsonPropertyName("total")]  public int               Total  { get; set; }
}

// =====================
// MODO MANTENIMIENTO
// =====================
public class MaintenanceStatus
{
    [JsonPropertyName("enabled")] public bool   Enabled { get; set; }
    [JsonPropertyName("message")] public string Message { get; set; } = "";
    [JsonPropertyName("since")]   public string? Since  { get; set; }
}

// =====================
// SEÑAL MT5
// =====================
public class Mt5Signal
{
    [JsonPropertyName("signal_id")]  public string SignalId  { get; set; } = "";
    [JsonPropertyName("action")]     public string Action    { get; set; } = "";
    [JsonPropertyName("confidence")] public double Confidence { get; set; }
    [JsonPropertyName("sl_pips")]    public double SlPips    { get; set; }
    [JsonPropertyName("tp_pips")]    public double TpPips    { get; set; }
    [JsonPropertyName("symbol")]     public string Symbol    { get; set; } = "";
    [JsonPropertyName("setup_name")] public string SetupName { get; set; } = "";
    [JsonPropertyName("timestamp")]  public string Timestamp { get; set; } = "";
}

// =====================
// RESPUESTAS API
// =====================
public class ApiResponse
{
    [JsonPropertyName("success")] public bool   Success { get; set; }
    [JsonPropertyName("message")] public string Message { get; set; } = "";
}

public class DebugEntry
{
    [JsonPropertyName("timestamp")] public string Timestamp { get; set; } = "";
    [JsonPropertyName("level")]     public string Level     { get; set; } = "";
    [JsonPropertyName("message")]   public string Message   { get; set; } = "";
}
