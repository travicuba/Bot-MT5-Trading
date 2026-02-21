using System.IO;
using System.Text.Json;

namespace TradingBotDesktop.Services;

public class AppSettings
{
    private static readonly string SettingsDir  = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "TradingBotDesktop");
    private static readonly string SettingsFile = Path.Combine(SettingsDir, "settings.json");

    // Conexion VPS
    public string VpsUrl  { get; set; } = "http://217.154.100.195:8080";
    public string ApiKey  { get; set; } = "";

    // Puente MT5
    public string Mt5FilesPath   { get; set; } = "";
    public bool   BridgeAutoStart { get; set; } = true;

    // UI
    public bool AutoRefresh      { get; set; } = true;
    public int  RefreshInterval  { get; set; } = 5;   // segundos

    public void Load()
    {
        try
        {
            if (!File.Exists(SettingsFile)) return;
            var json = File.ReadAllText(SettingsFile);
            var loaded = JsonSerializer.Deserialize<AppSettings>(json);
            if (loaded == null) return;

            VpsUrl        = loaded.VpsUrl;
            ApiKey        = loaded.ApiKey;
            Mt5FilesPath  = loaded.Mt5FilesPath;
            BridgeAutoStart = loaded.BridgeAutoStart;
            AutoRefresh   = loaded.AutoRefresh;
            RefreshInterval = loaded.RefreshInterval;
        }
        catch { /* ignorar error de carga */ }
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsFile, json);
        }
        catch { /* ignorar error de guardado */ }
    }
}
