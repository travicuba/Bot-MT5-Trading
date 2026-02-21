using System.IO;
using System.Text.Json;
using TradingBotDesktop.Models;

namespace TradingBotDesktop.Services;

/// <summary>
/// Servicio puente que sincroniza archivos entre el VPS (Python bot)
/// y el MT5 nativo instalado en Windows.
///
/// VPS -> PC:  signal.json, bot_status.json
/// PC  -> VPS: market_data.json, trade_feedback/*.json
/// </summary>
public class Mt5BridgeService
{
    private readonly ApiService _api;
    private string _mt5FilesPath = "";
    private CancellationTokenSource? _cts;
    private FileSystemWatcher? _signalWatcher;
    private FileSystemWatcher? _marketDataWatcher;
    private FileSystemWatcher? _feedbackWatcher;

    // Estado puente
    public bool   IsRunning   { get; private set; }
    public string StatusText  { get; private set; } = "Detenido";
    public int    SyncCount   { get; private set; }
    public string LastSync    { get; private set; } = "-";

    // Eventos
    public event EventHandler<string>? StatusChanged;
    public event EventHandler<string>? Error;
    public event EventHandler?         SyncOccurred;

    // Hash del ultimo market_data enviado (evitar duplicados)
    private string _lastMarketDataHash = "";

    // Set de feedbacks ya enviados
    private readonly HashSet<string> _sentFeedbacks = new();

    public Mt5BridgeService(ApiService api)
    {
        _api = api;
    }

    // =====================
    // INICIAR / DETENER
    // =====================
    public void Start(string mt5FilesPath)
    {
        if (IsRunning) return;

        _mt5FilesPath = mt5FilesPath;
        _cts          = new CancellationTokenSource();
        IsRunning     = true;
        StatusText    = "Conectando...";
        RaiseStatus("Conectando...");

        EnsureMt5Dirs();
        SetupWatchers();

        // Loops de polling
        Task.Run(() => SignalPollingLoop(_cts.Token));
        Task.Run(() => BotStatusPollingLoop(_cts.Token));
    }

    public void Stop()
    {
        if (!IsRunning) return;

        _cts?.Cancel();
        _signalWatcher?.Dispose();
        _marketDataWatcher?.Dispose();
        _feedbackWatcher?.Dispose();

        IsRunning  = false;
        StatusText = "Detenido";
        RaiseStatus("Detenido");
    }

    public void UpdateMt5Path(string newPath)
    {
        bool wasRunning = IsRunning;
        if (wasRunning) Stop();
        _mt5FilesPath = newPath;
        if (wasRunning) Start(newPath);
    }

    // =====================
    // DIRECTORIOS MT5
    // =====================
    private void EnsureMt5Dirs()
    {
        try
        {
            Directory.CreateDirectory(Path.Combine(_mt5FilesPath, "signals"));
            Directory.CreateDirectory(Path.Combine(_mt5FilesPath, "trade_feedback"));
        }
        catch (Exception ex)
        {
            RaiseError($"Error creando dirs MT5: {ex.Message}");
        }
    }

    // =====================
    // WATCHERS (PC -> VPS)
    // =====================
    private void SetupWatchers()
    {
        SetupSignalDeletionWatcher();
        SetupMarketDataWatcher();
        SetupFeedbackWatcher();
    }

    /// <summary>
    /// Detecta cuando el EA borra signal.json (señal consumida)
    /// y notifica al VPS para que Python envie la siguiente.
    /// </summary>
    private void SetupSignalDeletionWatcher()
    {
        var signalDir = Path.Combine(_mt5FilesPath, "signals");
        Directory.CreateDirectory(signalDir);

        _signalWatcher = new FileSystemWatcher(signalDir, "signal.json")
        {
            NotifyFilter        = NotifyFilters.FileName,
            EnableRaisingEvents = true,
        };
        _signalWatcher.Deleted += async (_, _) =>
        {
            try { await _api.ConsumeSignalAsync(); }
            catch { /* ignorar */ }
        };
    }

    /// <summary>
    /// Detecta cambios en market_data.json y los sube al VPS.
    /// </summary>
    private void SetupMarketDataWatcher()
    {
        try
        {
            _marketDataWatcher = new FileSystemWatcher(_mt5FilesPath, "market_data.json")
            {
                NotifyFilter        = NotifyFilters.LastWrite | NotifyFilters.Size,
                EnableRaisingEvents = true,
            };
            _marketDataWatcher.Changed += async (_, _) => await UploadMarketDataIfChanged();
            _marketDataWatcher.Created += async (_, _) => await UploadMarketDataIfChanged();
        }
        catch { /* directorio puede no existir aun */ }
    }

    /// <summary>
    /// Detecta nuevos archivos de feedback del EA y los sube al VPS.
    /// </summary>
    private void SetupFeedbackWatcher()
    {
        var feedbackDir = Path.Combine(_mt5FilesPath, "trade_feedback");
        Directory.CreateDirectory(feedbackDir);

        _feedbackWatcher = new FileSystemWatcher(feedbackDir, "*.json")
        {
            NotifyFilter        = NotifyFilters.FileName,
            EnableRaisingEvents = true,
        };
        _feedbackWatcher.Created += async (_, e) => await UploadFeedbackFile(e.FullPath);
    }

    // =====================
    // LOOPS VPS -> PC
    // =====================

    /// <summary>
    /// Cada 500ms: obtiene señal del VPS y la escribe en la carpeta MT5 local.
    /// </summary>
    private async Task SignalPollingLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                var signal = await _api.GetSignalAsync();
                if (signal != null)
                {
                    var signalPath = Path.Combine(_mt5FilesPath, "signals", "signal.json");
                    if (!File.Exists(signalPath))   // Solo escribir si no esta ya ahi
                    {
                        var json = JsonSerializer.Serialize(signal, new JsonSerializerOptions
                            { WriteIndented = true });
                        await File.WriteAllTextAsync(signalPath, json, ct);
                        RecordSync($"Señal: {signal.Action} {signal.SetupName}");
                    }
                }
            }
            catch (OperationCanceledException) { break; }
            catch { /* red caida, reintentar en siguiente ciclo */ }

            try { await Task.Delay(500, ct); } catch { break; }
        }
    }

    /// <summary>
    /// Cada 5s: descarga bot_status.json del VPS y lo escribe en MT5 local.
    /// </summary>
    private async Task BotStatusPollingLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                var statusElem = await _api.GetMt5BotStatusAsync();
                // ValueKind == Undefined significa que la llamada fallo
                if (statusElem.ValueKind != System.Text.Json.JsonValueKind.Undefined)
                {
                    var statusPath = Path.Combine(_mt5FilesPath, "bot_status.json");
                    var json = JsonSerializer.Serialize(statusElem,
                        new JsonSerializerOptions { WriteIndented = true });
                    await File.WriteAllTextAsync(statusPath, json, ct);
                    StatusText = "Activo";
                    RaiseStatus("Activo");
                }
            }
            catch (OperationCanceledException) { break; }
            catch
            {
                StatusText = "Sin conexion";
                RaiseStatus("Sin conexion");
            }

            try { await Task.Delay(5000, ct); } catch { break; }
        }
    }

    // =====================
    // UPLOADS PC -> VPS
    // =====================
    private async Task UploadMarketDataIfChanged()
    {
        try
        {
            await Task.Delay(200);  // Esperar a que el EA termine de escribir
            var path = Path.Combine(_mt5FilesPath, "market_data.json");
            if (!File.Exists(path)) return;

            var json = await File.ReadAllTextAsync(path);
            var hash = json.GetHashCode().ToString();
            if (hash == _lastMarketDataHash) return;
            _lastMarketDataHash = hash;

            var data = JsonSerializer.Deserialize<System.Text.Json.JsonElement>(json);
            await _api.UploadMarketDataAsync(data);
            RecordSync("Market data subido");
        }
        catch { /* ignorar errores transitorios */ }
    }

    private async Task UploadFeedbackFile(string filePath)
    {
        try
        {
            if (_sentFeedbacks.Contains(filePath)) return;
            _sentFeedbacks.Add(filePath);

            await Task.Delay(300);   // Esperar a que EA termine de escribir
            var json  = await File.ReadAllTextAsync(filePath);
            var elem  = JsonSerializer.Deserialize<System.Text.Json.JsonElement>(json);

            var signalId  = elem.GetProperty("signal_id").GetString() ?? "";
            var result    = elem.GetProperty("result").GetString() ?? "";
            var pips      = elem.GetProperty("pips").GetDouble();
            var timestamp = elem.TryGetProperty("timestamp", out var ts)
                ? ts.GetString() ?? DateTime.Now.ToString("o")
                : DateTime.Now.ToString("o");

            var resp = await _api.UploadFeedbackAsync(signalId, result, pips, timestamp);
            if (resp?.Success == true)
            {
                RecordSync($"Feedback: {result} {pips:F1} pips");
                // Opcional: borrar archivo local despues de enviar
                try { File.Delete(filePath); } catch { }
            }
        }
        catch { /* ignorar */ }
    }

    // =====================
    // HELPERS
    // =====================
    private void RecordSync(string description)
    {
        SyncCount++;
        LastSync = DateTime.Now.ToString("HH:mm:ss");
        SyncOccurred?.Invoke(this, EventArgs.Empty);
    }

    private void RaiseStatus(string msg)
        => StatusChanged?.Invoke(this, msg);

    private void RaiseError(string msg)
        => Error?.Invoke(this, msg);
}
