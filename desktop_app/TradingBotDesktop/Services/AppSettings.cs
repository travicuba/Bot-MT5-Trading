using System.IO;
using System.Text.Json;

namespace TradingBotDesktop.Services;

public class AppSettings
{
    private static AppSettings? _instance;
    public static AppSettings Instance => _instance ??= Load();

    private static readonly string SettingsDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "TradingBotDesktop");
    private static readonly string SettingsFile = Path.Combine(SettingsDir, "settings.json");

    // ── Servidor de usuarios (nuevo) ─────────────────────────────────────────
    public string ServerUrl      { get; set; } = "http://217.154.100.195:8000";

    // ── Sesión guardada ───────────────────────────────────────────────────────
    public string AuthToken      { get; set; } = "";
    public int    UserId         { get; set; } = 0;
    public bool   IsAdmin        { get; set; } = false;
    public string UserFirstName  { get; set; } = "";
    public string UserLastName   { get; set; } = "";
    public string UserEmail      { get; set; } = "";
    public string LicenseType    { get; set; } = "free";
    public bool   LicenseActive  { get; set; } = false;

    // ── Bot VPS API (bot Python) ─────────────────────────────────────────────
    public string VpsUrl         { get; set; } = "http://217.154.100.195:8080";
    public string ApiKey         { get; set; } = "";

    // ── Puente MT5 ────────────────────────────────────────────────────────────
    public string Mt5FilesPath   { get; set; } = "";
    public bool   BridgeAutoStart { get; set; } = true;

    // ── UI ────────────────────────────────────────────────────────────────────
    public bool AutoRefresh      { get; set; } = true;
    public int  RefreshInterval  { get; set; } = 5;

    private static AppSettings Load()
    {
        try
        {
            if (File.Exists(SettingsFile))
            {
                var json = File.ReadAllText(SettingsFile);
                var loaded = JsonSerializer.Deserialize<AppSettings>(json);
                if (loaded != null) return loaded;
            }
        }
        catch { }
        return new AppSettings();
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsFile, json);
        }
        catch { }
    }
}
