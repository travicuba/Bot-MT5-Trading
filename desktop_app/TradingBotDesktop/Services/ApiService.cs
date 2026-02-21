using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using TradingBotDesktop.Models;

namespace TradingBotDesktop.Services;

public class ApiService
{
    private readonly HttpClient _client;
    private string _baseUrl;
    private string _apiKey;

    private static readonly JsonSerializerOptions _jsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public ApiService(string baseUrl, string apiKey)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _apiKey  = apiKey;
        _client  = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(10),
        };
        SetApiKey(apiKey);
    }

    public void UpdateConnection(string baseUrl, string apiKey)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _apiKey  = apiKey;
        SetApiKey(apiKey);
    }

    private void SetApiKey(string key)
    {
        _client.DefaultRequestHeaders.Remove("X-API-Key");
        if (!string.IsNullOrEmpty(key))
            _client.DefaultRequestHeaders.Add("X-API-Key", key);
    }

    // =====================
    // HELPERS
    // =====================
    private async Task<T?> GetAsync<T>(string endpoint)
    {
        try
        {
            var resp = await _client.GetAsync($"{_baseUrl}{endpoint}");
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<T>(json, _jsonOpts);
        }
        catch { return default; }
    }

    private async Task<T?> PostAsync<T>(string endpoint, object? body = null)
    {
        try
        {
            HttpContent content = body != null
                ? new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json")
                : new StringContent("", Encoding.UTF8, "application/json");

            var resp = await _client.PostAsync($"{_baseUrl}{endpoint}", content);
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<T>(json, _jsonOpts);
        }
        catch { return default; }
    }

    private async Task<T?> PutAsync<T>(string endpoint, object body)
    {
        try
        {
            var content = new StringContent(
                JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
            var resp = await _client.PutAsync($"{_baseUrl}{endpoint}", content);
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<T>(json, _jsonOpts);
        }
        catch { return default; }
    }

    private async Task<bool> DeleteAsync(string endpoint)
    {
        try
        {
            var resp = await _client.DeleteAsync($"{_baseUrl}{endpoint}");
            return resp.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    // =====================
    // HEALTH CHECK
    // =====================
    public async Task<bool> PingAsync()
    {
        try
        {
            var resp = await _client.GetAsync($"{_baseUrl}/api/health");
            return resp.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    // =====================
    // BOT STATUS & CONTROL
    // =====================
    public Task<BotStatus?> GetStatusAsync()
        => GetAsync<BotStatus>("/api/status");

    public Task<ApiResponse?> StartBotAsync()
        => PostAsync<ApiResponse>("/api/bot/start");

    public Task<ApiResponse?> StopBotAsync()
        => PostAsync<ApiResponse>("/api/bot/stop");

    // =====================
    // CONFIG
    // =====================
    public Task<BotConfig?> GetConfigAsync()
        => GetAsync<BotConfig>("/api/config");

    public Task<JsonElement?> UpdateConfigAsync(object configUpdate)
        => PutAsync<JsonElement>("/api/config", configUpdate);

    // =====================
    // STATS & HISTORY
    // =====================
    public Task<BotStats?> GetStatsAsync()
        => GetAsync<BotStats>("/api/stats");

    public Task<HistoryResponse?> GetHistoryAsync(int limit = 100, int offset = 0)
        => GetAsync<HistoryResponse>($"/api/history?limit={limit}&offset={offset}");

    public Task<List<DebugEntry>?> GetDebugAsync(int limit = 100)
        => GetAsync<List<DebugEntry>>($"/api/debug?limit={limit}");

    // =====================
    // MAINTENANCE
    // =====================
    public Task<MaintenanceStatus?> GetMaintenanceAsync()
        => GetAsync<MaintenanceStatus>("/api/maintenance");

    public Task<JsonElement?> SetMaintenanceAsync(bool enabled, string message = "")
        => PutAsync<JsonElement>("/api/maintenance", new { enabled, message });

    // =====================
    // PUENTE MT5
    // =====================
    public Task<Mt5Signal?> GetSignalAsync()
        => GetAsync<Mt5Signal>("/api/mt5/signal");

    public Task<bool> ConsumeSignalAsync()
        => DeleteAsync("/api/mt5/signal");

    public Task<JsonElement?> GetMt5BotStatusAsync()
        => GetAsync<JsonElement>("/api/mt5/bot_status");

    public Task<JsonElement?> UploadMarketDataAsync(object data)
        => PutAsync<JsonElement>("/api/mt5/market_data", new { data });

    public Task<ApiResponse?> UploadFeedbackAsync(
        string signalId, string result, double pips, string timestamp)
        => PostAsync<ApiResponse>("/api/mt5/feedback", new
        {
            signal_id = signalId,
            result,
            pips,
            timestamp,
        });
}
