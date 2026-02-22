using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TradingBotDesktop.Services;

// ── DTOs ──────────────────────────────────────────────────────────────────────

public class MaintenanceInfo
{
    [JsonPropertyName("enabled")] public bool   Enabled { get; set; }
    [JsonPropertyName("message")] public string Message { get; set; } = "";
}

public class BotConfigDto
{
    [JsonPropertyName("bot_type")]   public string                  BotType   { get; set; } = "";
    [JsonPropertyName("config")]     public Dictionary<string, object> Config { get; set; } = new();
    [JsonPropertyName("api_key")]    public string?                 ApiKey    { get; set; }
    [JsonPropertyName("mt5_account")] public string?               Mt5Account { get; set; }
    [JsonPropertyName("mt5_server")] public string?                Mt5Server { get; set; }
    [JsonPropertyName("updated_at")] public DateTime?              UpdatedAt { get; set; }
}

// ── Service ───────────────────────────────────────────────────────────────────

public static class ServerApiService
{
    private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(10) };
    private static readonly JsonSerializerOptions _jOpt = new() { PropertyNameCaseInsensitive = true };

    private static string Base => AppSettings.Instance.ServerUrl.TrimEnd('/');

    private static void SetAuth()
    {
        _http.DefaultRequestHeaders.Remove("Authorization");
        var token = AppSettings.Instance.AuthToken;
        if (!string.IsNullOrEmpty(token))
            _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {token}");
    }

    // ── MAINTENANCE ────────────────────────────────────────────────────────

    public static async Task<MaintenanceInfo> CheckMaintenanceAsync()
    {
        try
        {
            var response = await _http.GetAsync($"{Base}/system/maintenance");
            if (response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync();
                return JsonSerializer.Deserialize<MaintenanceInfo>(body, _jOpt)
                       ?? new MaintenanceInfo();
            }
        }
        catch { }
        return new MaintenanceInfo { Enabled = false };
    }

    // ── BOT CONFIG ─────────────────────────────────────────────────────────

    public static async Task<BotConfigDto?> GetBotConfigAsync(string botType)
    {
        try
        {
            SetAuth();
            var response = await _http.GetAsync($"{Base}/config/{botType}");
            if (response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync();
                return JsonSerializer.Deserialize<BotConfigDto>(body, _jOpt);
            }
        }
        catch { }
        return null;
    }

    public static async Task<bool> SaveBotConfigAsync(string botType, Dictionary<string, object> config,
        string? apiKey = null, string? apiSecret = null, string? mt5Account = null,
        string? mt5Password = null, string? mt5Server = null)
    {
        try
        {
            SetAuth();
            var payload = new
            {
                config,
                api_key     = apiKey,
                api_secret  = apiSecret,
                mt5_account = mt5Account,
                mt5_password = mt5Password,
                mt5_server  = mt5Server,
            };
            var response = await _http.PutAsJsonAsync($"{Base}/config/{botType}", payload);
            return response.IsSuccessStatusCode;
        }
        catch { return false; }
    }
}
