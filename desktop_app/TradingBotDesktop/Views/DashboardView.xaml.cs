using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace TradingBotDesktop.Views;

public partial class DashboardView : Page, IRefreshable
{
    private readonly DispatcherTimer _refreshTimer = new();
    private bool _botRunning = false;

    public DashboardView()
    {
        InitializeComponent();

        // Bridge status events
        App.Bridge.StatusChanged += (_, msg) =>
            Dispatcher.Invoke(() =>
            {
                BridgeStatusText.Text = msg;
                BridgeStatusText.Foreground = msg == "Activo"
                    ? (Brush)Application.Current.FindResource("SuccessBrush")
                    : (Brush)Application.Current.FindResource("ErrorBrush");
            });

        App.Bridge.SyncOccurred += (_, _) =>
            Dispatcher.Invoke(() =>
            {
                SyncCountText.Text = App.Bridge.SyncCount.ToString();
                LastSyncText.Text  = App.Bridge.LastSync;
            });

        // Auto refresh
        _refreshTimer.Interval = TimeSpan.FromSeconds(
            App.Settings.AutoRefresh ? App.Settings.RefreshInterval : 30);
        _refreshTimer.Tick += async (_, _) => await RefreshAsync();
        _refreshTimer.Start();

        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        try
        {
            var status = await App.Api.GetStatusAsync();
            var stats  = await App.Api.GetStatsAsync();

            Dispatcher.Invoke(() =>
            {
                // Estado bot
                if (status != null)
                {
                    _botRunning = status.Running;
                    var running = status.Running;

                    BotStatusDot.Fill     = running
                        ? (Brush)Application.Current.FindResource("SuccessBrush")
                        : (Brush)Application.Current.FindResource("ErrorBrush");
                    BotStatusText.Text       = running ? "EN EJECUCION" : "DETENIDO";
                    BotStatusText.Foreground = running
                        ? (Brush)Application.Current.FindResource("SuccessBrush")
                        : (Brush)Application.Current.FindResource("ErrorBrush");

                    UptimeText.Text      = status.UptimeFormatted;
                    PidText.Text         = status.Pid?.ToString() ?? "-";
                    ActiveTradesText.Text = status.ActiveTrades.ToString();

                    BtnStart.IsEnabled = !running;
                    BtnStop.IsEnabled  = running;
                }

                // Estadisticas
                if (stats != null)
                {
                    // Hoy
                    TodayTrades.Text = stats.Today.Trades.ToString();
                    TodayWins.Text   = stats.Today.Wins.ToString();
                    TodayWinRate.Text = $"{stats.Today.WinRate:F0}%";
                    TodayPips.Text   = stats.Today.Pips.ToString("F1");
                    TotalTrades.Text = stats.TotalTrades.ToString();

                    // Global
                    GlobalWinRate.Text = $"{stats.WinRate:F1}%";
                    GlobalPips.Text    = stats.TotalPips.ToString("F1");
                    WinsLosses.Text    = $"{stats.Wins} / {stats.Losses}";

                    // Semana
                    WeekTrades.Text   = stats.Week.Trades.ToString();
                    WeekWinRate.Text  = $"{stats.Week.WinRate:F0}%";
                    WeekPips.Text     = stats.Week.Pips.ToString("F1");

                    // Colores de pips
                    var pipColor = stats.Today.Pips >= 0
                        ? (Brush)Application.Current.FindResource("SuccessBrush")
                        : (Brush)Application.Current.FindResource("ErrorBrush");
                    TodayPips.Foreground = pipColor;

                    var globalPipColor = stats.TotalPips >= 0
                        ? (Brush)Application.Current.FindResource("SuccessBrush")
                        : (Brush)Application.Current.FindResource("ErrorBrush");
                    GlobalPips.Foreground = globalPipColor;

                    var weekPipColor = stats.Week.Pips >= 0
                        ? (Brush)Application.Current.FindResource("SuccessBrush")
                        : (Brush)Application.Current.FindResource("ErrorBrush");
                    WeekPips.Foreground = weekPipColor;
                }

                // Bridge
                SyncCountText.Text = App.Bridge.SyncCount.ToString();
                LastSyncText.Text  = App.Bridge.LastSync;

                LastUpdate.Text = $"Actualizado: {DateTime.Now:HH:mm:ss}";
            });
        }
        catch { /* red caida, ignorar */ }
    }

    private async void BtnStart_Click(object sender, RoutedEventArgs e)
    {
        BtnStart.IsEnabled = false;
        BtnStart.Content   = "Iniciando...";

        var resp = await App.Api.StartBotAsync();
        if (resp?.Success == true)
        {
            await RefreshAsync();
            MessageBox.Show("Bot iniciado correctamente.", "Bot MT5",
                MessageBoxButton.OK, MessageBoxImage.Information);
        }
        else
        {
            MessageBox.Show($"Error al iniciar: {resp?.Message ?? "Sin respuesta del VPS"}",
                "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
            BtnStart.IsEnabled = true;
        }
        BtnStart.Content = "INICIAR BOT";
    }

    private async void BtnStop_Click(object sender, RoutedEventArgs e)
    {
        var confirm = MessageBox.Show("¿Detener el bot?", "Confirmar",
            MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (confirm != MessageBoxResult.Yes) return;

        BtnStop.IsEnabled = false;
        BtnStop.Content   = "Deteniendo...";

        var resp = await App.Api.StopBotAsync();
        await RefreshAsync();

        BtnStop.Content   = "DETENER BOT";
    }
}
