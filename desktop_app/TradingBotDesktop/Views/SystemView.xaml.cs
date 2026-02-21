using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using TradingBotDesktop.Models;

namespace TradingBotDesktop.Views;

public partial class SystemView : Page, IRefreshable
{
    public SystemView()
    {
        InitializeComponent();

        App.Bridge.StatusChanged += (_, msg) =>
            Dispatcher.Invoke(() => UpdateBridgeUi(msg));

        App.Bridge.SyncOccurred += (_, _) =>
            Dispatcher.Invoke(() =>
            {
                SyncCountLabel.Text = App.Bridge.SyncCount.ToString();
                LastSyncLabel.Text  = App.Bridge.LastSync;
            });

        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        VpsUrlText.Text = App.Settings.VpsUrl;
        Mt5PathText.Text = string.IsNullOrEmpty(App.Settings.Mt5FilesPath)
            ? "(No configurado)"
            : App.Settings.Mt5FilesPath;

        UpdateBridgeUi(App.Bridge.IsRunning ? "Activo" : "Detenido");
        SyncCountLabel.Text = App.Bridge.SyncCount.ToString();
        LastSyncLabel.Text  = App.Bridge.LastSync;

        await CheckConnection();
        await LoadLogs();
    }

    private async Task CheckConnection()
    {
        var sw    = System.Diagnostics.Stopwatch.StartNew();
        bool ping = await App.Api.PingAsync();
        sw.Stop();

        Dispatcher.Invoke(() =>
        {
            VpsStatusDot.Fill  = ping
                ? (Brush)Application.Current.FindResource("SuccessBrush")
                : (Brush)Application.Current.FindResource("ErrorBrush");
            VpsStatusText.Text = ping ? "Conectado" : "Sin conexion";
            LatencyText.Text   = ping ? $"{sw.ElapsedMilliseconds} ms" : "-";
        });
    }

    private async Task LoadLogs()
    {
        var logs = await App.Api.GetDebugAsync(200);
        if (logs == null) return;

        Dispatcher.Invoke(() =>
        {
            LogList.Items.Clear();
            foreach (var entry in logs)
            {
                var color = entry.Level switch
                {
                    "ERROR" => Brushes.Tomato,
                    "WARN"  => Brushes.Goldenrod,
                    "INFO"  => Brushes.LightGray,
                    _       => Brushes.Gray,
                };

                var tb = new TextBlock
                {
                    Text       = $"[{entry.Timestamp}] [{entry.Level,-5}] {entry.Message}",
                    Foreground = color,
                    FontFamily = new FontFamily("Consolas"),
                    FontSize   = 11,
                    Margin     = new Thickness(4, 1, 4, 1),
                };
                LogList.Items.Add(tb);
            }

            // Scroll al final (ultimo log)
            if (LogList.Items.Count > 0)
                LogList.ScrollIntoView(LogList.Items[LogList.Items.Count - 1]);
        });
    }

    private void UpdateBridgeUi(string status)
    {
        bool active = status == "Activo";
        BridgeStatusDot.Fill    = active
            ? (Brush)Application.Current.FindResource("SuccessBrush")
            : (Brush)Application.Current.FindResource("ErrorBrush");
        BridgeStatusLabel.Text  = status;
        BtnBridgeToggle.Content = active ? "Detener Puente" : "Iniciar Puente";
        BtnBridgeToggle.Style   = active
            ? (Style)Application.Current.FindResource("DangerButton")
            : (Style)Application.Current.FindResource("SuccessButton");
    }

    private async void BtnPing_Click(object sender, RoutedEventArgs e)
        => await CheckConnection();

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
        => await RefreshAsync();

    private async void BtnRefreshLogs_Click(object sender, RoutedEventArgs e)
        => await LoadLogs();

    private void BtnBridgeToggle_Click(object sender, RoutedEventArgs e)
    {
        if (App.Bridge.IsRunning)
        {
            App.Bridge.Stop();
        }
        else
        {
            if (string.IsNullOrEmpty(App.Settings.Mt5FilesPath))
            {
                MessageBox.Show(
                    "Primero configura la ruta de la carpeta Files de MT5 en 'Conexion VPS'.",
                    "Configuracion requerida",
                    MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }
            App.Bridge.Start(App.Settings.Mt5FilesPath);
        }
    }
}
