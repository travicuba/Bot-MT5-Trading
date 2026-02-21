using System.Net.Http;
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
        _client  = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        SetApiKey(apiKey);
    }

    public void UpdateConnection(string baseUrl, string apiKey)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        SetApiKey(apiKey);
    }

    private void SetApiKey(string key)
    {
        _client.DefaultRequestHeaders.Remove("X-API-Key");
        if (!string.IsNullOrEmpty(key))
            _client.DefaultRequestHeaders.Add("X-API-Key", key);
    }

    // =====================
    // HELPERS - clase (reference types)
    // =====================
    private async Task<T?> GetAsync<T>(string endpoint) where T : class
    {
        try
        {
            var resp = await _client.GetAsync($"{_baseUrl}{endpoint}");
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<T>(json, _jsonOpts);
        }
        catch { return null; }
    }

    private async Task<T?> PostAsync<T>(string endpoint, object? body = null) where T : class
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
        catch { return null; }
    }

    // Helper para PUT/DELETE que solo necesita saber si fue exitoso
    private async Task<bool> PutBoolAsync(string endpoint, object body)
    {
        try
        {
            var content = new StringContent(
                JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
            var resp = await _client.PutAsync($"{_baseUrl}{endpoint}", content);
            return resp.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    // Helper para GET que devuelve JsonElement (struct - no puede ser nullable generico)
    private async Task<JsonElement> GetJsonAsync(string endpoint)
    {
        try
        {
            var resp = await _client.GetAsync($"{_baseUrl}{endpoint}");
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<JsonElement>(json, _jsonOpts);
        }
        catch { return default; }   // ValueKind == Undefined indica fallo
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

    /// <summary>Retorna true si la config se guardó correctamente.</summary>
    public Task<bool> UpdateConfigAsync(object configUpdate)
        => PutBoolAsync("/api/config", configUpdate);

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

    /// <summary>Retorna true si el modo mantenimiento se actualizó.</summary>
    public Task<bool> SetMaintenanceAsync(bool enabled, string message = "")
        => PutBoolAsync("/api/maintenance", new { enabled, message });

    // =====================
    // PUENTE MT5
    // =====================
    public Task<Mt5Signal?> GetSignalAsync()
        => GetAsync<Mt5Signal>("/api/mt5/signal");

    public Task<bool> ConsumeSignalAsync()
        => DeleteAsync("/api/mt5/signal");

    /// <summary>
    /// Devuelve bot_status como JsonElement.
    /// Verificar: result.ValueKind != JsonValueKind.Undefined antes de usar.
    /// </summary>
    public Task<JsonElement> GetMt5BotStatusAsync()
        => GetJsonAsync("/api/mt5/bot_status");

    /// <summary>Retorna true si market_data se subió correctamente.</summary>
    public Task<bool> UploadMarketDataAsync(object data)
        => PutBoolAsync("/api/mt5/market_data", new { data });

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
