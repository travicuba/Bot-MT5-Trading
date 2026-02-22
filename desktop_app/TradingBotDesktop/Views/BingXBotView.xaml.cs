using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using System.Text.Json;
using System.Net.Http;
using System.Net.Http.Json;
using TradingBotDesktop.Services;

namespace TradingBotDesktop.Views;

public record BxHistRow(string Date, string Symbol, string Direction, string Result, string Pnl, string Entry);
public record BxPosRow(string Symbol, string Side, string Pnl);

public partial class BingXBotView : Page
{
    private readonly MainWindow      _main;
    private readonly DispatcherTimer _refreshTimer = new();

    public BingXBotView(MainWindow main)
    {
        InitializeComponent();
        _main = main;

        _refreshTimer.Interval = TimeSpan.FromSeconds(8);
        _refreshTimer.Tick    += (_, _) => _ = RefreshAll();
        _refreshTimer.Start();

        Loaded   += async (_, _) => await RefreshAll();
        Unloaded += (_, _) => _refreshTimer.Stop();
    }

    // ── Refresh ───────────────────────────────────────────────────────────────

    private async Task RefreshAll()
    {
        try
        {
            await RefreshStats();
            await RefreshHistory();
            RefreshSysGrid();
        }
        catch { }
    }

    private async Task RefreshStats()
    {
        try
        {
            // Load BingX stats from VPS via /api/status or local json
            // For now, show info from AppSettings + server
            var cfg = await ServerApiService.GetBotConfigAsync("bingx");
            if (cfg != null)
            {
                if (cfg.ApiKey != null) ApiKey.Text = cfg.ApiKey;
            }
        }
        catch { }
    }

    private async Task RefreshHistory()
    {
        try
        {
            var history = await App.Api.GetHistoryJsonAsync();
            var rows = new List<BxHistRow>();
            if (history.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in history.EnumerateArray())
                {
                    string date   = item.TryGetProperty("timestamp",  out var d) ? d.GetString() ?? "—" : "—";
                    string sym    = item.TryGetProperty("symbol",     out var s) ? s.GetString() ?? "—" : "—";
                    string dir    = item.TryGetProperty("direction",  out var di) ? di.GetString() ?? "—" : "—";
                    string res    = item.TryGetProperty("result",     out var r) ? r.GetString() ?? "—" : "—";
                    string pnl    = item.TryGetProperty("pnl",        out var p) ? p.ToString() : "—";
                    string entry  = item.TryGetProperty("entry_price",out var e) ? e.ToString() : "—";
                    rows.Add(new BxHistRow(date, sym, dir, res, pnl, entry));
                }
            }
            HistoryGrid.ItemsSource = rows;

            // Stats summary
            int total = rows.Count;
            int wins  = rows.Count(r => r.Result == "WIN");
            StTotalTrades.Text = total.ToString();
            StWinRate.Text     = total > 0 ? $"{(double)wins / total * 100:F0}%" : "0%";
        }
        catch { }
    }

    private void RefreshSysGrid()
    {
        var rows = new List<SysRow>
        {
            new("Servidor usuario", AppSettings.Instance.ServerUrl),
            new("Servidor VPS",     AppSettings.Instance.VpsUrl),
            new("Licencia",         AppSettings.Instance.LicenseType),
            new("Usuario",          AppSettings.Instance.UserEmail),
            new("Actualizado",      DateTime.Now.ToString("HH:mm:ss")),
        };
        SysGrid.ItemsSource = rows;
    }

    // ── Bot controls ──────────────────────────────────────────────────────────

    private async void StartBot_Click(object sender, RoutedEventArgs e)
    {
        StartBtn.IsEnabled = false;
        try
        {
            // The BingX bot runs on the Python side (bingx_gui.py)
            // The WPF client shows status; actual control is in Python app
            MessageBox.Show("El bot BingX se controla desde la aplicación Python en el VPS.\n" +
                            "Abre la terminal del servidor y ejecuta:\n\n  python launcher.py",
                            "BingX Bot", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        finally { StartBtn.IsEnabled = true; }
    }

    private void StopBot_Click(object sender, RoutedEventArgs e) { }

    // ── Config ────────────────────────────────────────────────────────────────

    private async void SaveConfig_Click(object sender, RoutedEventArgs e)
    {
        ConfigStatus.Text = "Guardando...";
        try
        {
            var config = new Dictionary<string, object>
            {
                ["default_symbol"]   = CfgSymbol.Text,
                ["default_leverage"] = int.TryParse(CfgLeverage.Text, out var lv) ? lv : 10,
                ["risk_percent"]     = double.TryParse(CfgRisk.Text, out var rk) ? rk : 1.0,
                ["cooldown"]         = int.TryParse(CfgCooldown.Text, out var cd) ? cd : 60,
                ["min_confidence"]   = int.TryParse(CfgMinConf.Text, out var mc) ? mc : 30,
            };
            await ServerApiService.SaveBotConfigAsync("bingx", config);
            ConfigStatus.Text = "✓ Configuración guardada en la nube";
        }
        catch (Exception ex)
        {
            ConfigStatus.Text = $"✗ Error: {ex.Message}";
        }
    }

    private async void SaveCreds_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await ServerApiService.SaveBotConfigAsync("bingx",
                new Dictionary<string, object>(),
                apiKey: ApiKey.Text,
                apiSecret: ApiSecret.Password);
            MessageBox.Show("Credenciales guardadas en el servidor.", "OK",
                            MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
