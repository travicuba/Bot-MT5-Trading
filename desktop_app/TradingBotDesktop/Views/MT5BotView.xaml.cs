using System.Windows;
using System.Windows.Controls;
using System.Windows.Forms;
using System.Windows.Threading;
using System.Text.Json;
using TradingBotDesktop.Services;

namespace TradingBotDesktop.Views;

public record StatRow(string Setup, int Trades, int Wins, int Losses, string WinRate, string Pips);
public record HistRow(string Date, string Symbol, string Action, string Result, string Pips, string Setup);
public record SysRow(string Key, string Value);

public partial class MT5BotView : Page
{
    private readonly MainWindow       _main;
    private readonly DispatcherTimer  _refreshTimer = new();

    public MT5BotView(MainWindow main)
    {
        InitializeComponent();
        _main = main;

        BridgePath.Text = string.IsNullOrEmpty(AppSettings.Instance.Mt5FilesPath)
                          ? "Sin configurar" : AppSettings.Instance.Mt5FilesPath;

        _refreshTimer.Interval = TimeSpan.FromSeconds(5);
        _refreshTimer.Tick    += async (_, _) => await RefreshAll();
        _refreshTimer.Start();

        Loaded += async (_, _) => await RefreshAll();
        Unloaded += (_, _) => _refreshTimer.Stop();
    }

    // ── Refresh ───────────────────────────────────────────────────────────────

    private async Task RefreshAll()
    {
        try
        {
            await RefreshStatus();
            UpdateBridgeStatus();
            UpdateAiPanel();
        }
        catch { }
    }

    private async Task RefreshStatus()
    {
        try
        {
            var status = await App.Api.GetBotStatusAsync();
            if (status.ValueKind == JsonValueKind.Undefined) return;

            bool running = status.TryGetProperty("running", out var r) && r.GetBoolean();
            SetBotStatus(running);
            _main.SetMt5Status(running);

            if (status.TryGetProperty("stats_today", out var st))
            {
                int trades   = st.TryGetProperty("trades",   out var t) ? t.GetInt32() : 0;
                int wins     = st.TryGetProperty("wins",     out var w) ? w.GetInt32() : 0;
                double pips  = st.TryGetProperty("pips",    out var p) ? p.GetDouble() : 0;
                double winRate = trades > 0 ? (double)wins / trades * 100 : 0;
                StatTrades.Text  = trades.ToString();
                StatWins.Text    = wins.ToString();
                StatWinRate.Text = $"{winRate:F0}%";
                StatPips.Text    = pips.ToString("F1");
                TodayTrades.Text = $"Trades: {trades}";
                TodayPnl.Text    = $"Pips: {pips:F1}";
            }

            if (status.TryGetProperty("last_signal", out var sig))
            {
                CurrentSignal.Text = sig.GetString() ?? "—";
                ConnDot.Fill       = new System.Windows.Media.SolidColorBrush(
                    System.Windows.Media.Color.FromRgb(0x06, 0xFF, 0xA5));
                ConnStatus.Text    = "CONECTADO";
                ConnStatus.Foreground = System.Windows.Media.Brushes.LimeGreen;
            }
        }
        catch { }
    }

    private void SetBotStatus(bool running)
    {
        if (running)
        {
            BotDot.Fill    = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(0x06, 0xFF, 0xA5));
            BotStatus.Text = "ACTIVO";
            BotStatus.Foreground = System.Windows.Media.Brushes.LimeGreen;
            BotInfo.Text   = "Bot ejecutándose";
            StartBtn.IsEnabled = false;
            StopBtn.IsEnabled  = true;
        }
        else
        {
            BotDot.Fill    = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(0xFF, 0x00, 0x6E));
            BotStatus.Text = "DETENIDO";
            BotStatus.Foreground = System.Windows.Media.Brushes.Tomato;
            BotInfo.Text   = "Bot inactivo";
            StartBtn.IsEnabled = true;
            StopBtn.IsEnabled  = false;
        }
    }

    private void UpdateBridgeStatus()
    {
        bool active = App.Bridge.IsRunning;
        BridgeDot.Fill = new System.Windows.Media.SolidColorBrush(
            active
                ? System.Windows.Media.Color.FromRgb(0x06, 0xFF, 0xA5)
                : System.Windows.Media.Color.FromRgb(0x55, 0x55, 0x55));
        BridgeStatus.Text = active ? "Activo" : "Inactivo";
    }

    private void UpdateAiPanel()
    {
        AiPanel.Text =
            $"Servidor VPS: {AppSettings.Instance.VpsUrl}\n" +
            $"Puente MT5: {(App.Bridge.IsRunning ? "Activo" : "Inactivo")}\n" +
            $"Última actualización: {DateTime.Now:HH:mm:ss}\n\n" +
            "IA: El sistema analiza señales automáticamente.\n" +
            "Revisa el dashboard del bot Python en VPS para\n" +
            "ver el análisis completo del mercado.";
    }

    // ── Bot controls ──────────────────────────────────────────────────────────

    private async void StartBot_Click(object sender, RoutedEventArgs e)
    {
        StartBtn.IsEnabled = false;
        try
        {
            await App.Api.StartBotAsync();
            await Task.Delay(500);
            await RefreshStatus();
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"Error al iniciar: {ex.Message}", "Error");
        }
        finally { StartBtn.IsEnabled = true; }
    }

    private async void StopBot_Click(object sender, RoutedEventArgs e)
    {
        StopBtn.IsEnabled = false;
        try
        {
            await App.Api.StopBotAsync();
            await Task.Delay(500);
            await RefreshStatus();
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"Error al detener: {ex.Message}", "Error");
        }
        finally { StopBtn.IsEnabled = true; }
    }

    // ── Bridge ────────────────────────────────────────────────────────────────

    private void ConfigureBridge_Click(object sender, RoutedEventArgs e)
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "Selecciona la carpeta Files de MT5\n(MetaTrader 5\\MQL5\\Files)"
        };
        if (dlg.ShowDialog() == DialogResult.OK)
        {
            AppSettings.Instance.Mt5FilesPath = dlg.SelectedPath;
            AppSettings.Instance.Save();
            BridgePath.Text = dlg.SelectedPath;
            App.Bridge.Start(dlg.SelectedPath);
            UpdateBridgeStatus();
        }
    }

    // ── Stats ─────────────────────────────────────────────────────────────────

    private async void RefreshStats_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var stats = await App.Api.GetStatsJsonAsync();
            var rows = new List<StatRow>();
            if (stats.TryGetProperty("setup_stats", out var ss))
            {
                foreach (var prop in ss.EnumerateObject())
                {
                    var v = prop.Value;
                    int t = v.TryGetProperty("total", out var tv) ? tv.GetInt32() : 0;
                    int w = v.TryGetProperty("wins",  out var wv) ? wv.GetInt32() : 0;
                    int l = v.TryGetProperty("losses",out var lv) ? lv.GetInt32() : 0;
                    double p = v.TryGetProperty("pips",out var pv) ? pv.GetDouble() : 0;
                    string wr = t > 0 ? $"{(double)w / t * 100:F0}%" : "—";
                    rows.Add(new StatRow(prop.Name, t, w, l, wr, p.ToString("F1")));
                }
            }
            StatsGrid.ItemsSource = rows;
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"Error al cargar estadísticas: {ex.Message}");
        }
    }

    private async void RefreshSys_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var debug = await App.Api.GetDebugJsonAsync();
            var rows = new List<SysRow>
            {
                new("Servidor VPS",    AppSettings.Instance.VpsUrl),
                new("Servidor usuario",AppSettings.Instance.ServerUrl),
                new("Puente MT5",      App.Bridge.IsRunning ? "Activo" : "Inactivo"),
                new("Ruta MT5",        AppSettings.Instance.Mt5FilesPath),
                new("Licencia",        AppSettings.Instance.LicenseType),
                new("Usuario",         AppSettings.Instance.UserEmail),
                new("Última consulta", DateTime.Now.ToString("HH:mm:ss")),
            };
            if (debug.ValueKind != JsonValueKind.Undefined)
            {
                foreach (var p in debug.EnumerateObject())
                    rows.Add(new SysRow(p.Name, p.Value.ToString()));
            }
            SysGrid.ItemsSource = rows;
        }
        catch { }
    }

    // ── Config ────────────────────────────────────────────────────────────────

    private async void SaveConfig_Click(object sender, RoutedEventArgs e)
    {
        ConfigStatus.Text = "Guardando...";
        try
        {
            var config = new Dictionary<string, object>
            {
                ["min_confidence"]    = double.TryParse(CfgMinConf.Text, out var mc) ? mc : 5.0,
                ["cooldown"]          = int.TryParse(CfgCooldown.Text, out var cd) ? cd : 30,
                ["max_daily_trades"]  = int.TryParse(CfgMaxTrades.Text, out var mt) ? mt : 50,
                ["lot_size"]          = double.TryParse(CfgLotSize.Text, out var ls) ? ls : 0.01,
                ["max_losses"]        = int.TryParse(CfgMaxLoss.Text, out var ml) ? ml : 5,
            };

            // Save to VPS bot API
            await App.Api.UpdateConfigAsync(config);

            // Save to user server (cloud sync)
            await ServerApiService.SaveBotConfigAsync("mt5", config);

            ConfigStatus.Text = "✓ Guardado correctamente";
        }
        catch (Exception ex)
        {
            ConfigStatus.Text = $"✗ Error: {ex.Message}";
        }
    }

    private async void SaveMt5Creds_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await ServerApiService.SaveBotConfigAsync("mt5",
                new Dictionary<string, object>(),
                mt5Account: Mt5Account.Text,
                mt5Password: Mt5Password.Password,
                mt5Server: Mt5Server.Text);
            System.Windows.MessageBox.Show("Credenciales guardadas en el servidor.", "OK");
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"Error: {ex.Message}");
        }
    }
}
