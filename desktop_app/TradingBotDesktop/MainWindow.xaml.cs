using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using TradingBotDesktop.Views;

namespace TradingBotDesktop;

public partial class MainWindow : Window
{
    private readonly DispatcherTimer _clockTimer      = new();
    private readonly DispatcherTimer _statusTimer     = new();
    private readonly DispatcherTimer _maintenanceTimer = new();

    private Button? _activeNavBtn;

    // Paginas (creadas una sola vez)
    private readonly DashboardView      _dashboard      = new();
    private readonly StatisticsView     _statistics     = new();
    private readonly HistoryView        _history        = new();
    private readonly ConfigurationView  _configuration  = new();
    private readonly SystemView         _system         = new();
    private readonly SettingsView       _settings       = new();

    public MainWindow()
    {
        InitializeComponent();
        _activeNavBtn = BtnDashboard;

        // Navegar al dashboard al iniciar
        MainFrame.Navigate(_dashboard);

        // Reloj
        _clockTimer.Interval = TimeSpan.FromSeconds(1);
        _clockTimer.Tick += (_, _) =>
            ClockText.Text = DateTime.Now.ToString("HH:mm:ss");
        _clockTimer.Start();

        // Estado de conexion (cada 5s)
        _statusTimer.Interval = TimeSpan.FromSeconds(5);
        _statusTimer.Tick += async (_, _) => await RefreshConnectionStatus();
        _statusTimer.Start();

        // Verificar mantenimiento (cada 30s)
        _maintenanceTimer.Interval = TimeSpan.FromSeconds(30);
        _maintenanceTimer.Tick += async (_, _) => await CheckMaintenance();
        _maintenanceTimer.Start();

        // Estado del puente
        App.Bridge.StatusChanged += (_, msg) =>
            Dispatcher.Invoke(() =>
            {
                bool active = msg == "Activo";
                BridgeDot.Fill  = active
                    ? (Brush)FindResource("SuccessBrush")
                    : (Brush)FindResource("ErrorBrush");
                BridgeText.Text = $"Puente MT5: {(active ? "on" : "off")}";
            });

        // Primer check al cargar
        Loaded += async (_, _) =>
        {
            await RefreshConnectionStatus();
            await CheckMaintenance();
        };
    }

    // =====================
    // NAVEGACION
    // =====================
    private void NavButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn) return;

        // Cambiar estilo del boton activo
        if (_activeNavBtn != null)
            _activeNavBtn.Style = (Style)FindResource("NavButton");
        btn.Style    = (Style)FindResource("NavButtonActive");
        _activeNavBtn = btn;

        // Navegar a la vista correspondiente
        Page? page = btn.Tag?.ToString() switch
        {
            "Dashboard"     => _dashboard,
            "Statistics"    => _statistics,
            "History"       => _history,
            "Configuration" => _configuration,
            "System"        => _system,
            "Settings"      => _settings,
            _               => null,
        };

        if (page != null)
            MainFrame.Navigate(page);

        // Recargar datos de la vista
        if (page is IRefreshable r)
            _ = r.RefreshAsync();
    }

    // =====================
    // ESTADO DE CONEXION
    // =====================
    private async Task RefreshConnectionStatus()
    {
        bool connected = await App.Api.PingAsync();
        Dispatcher.Invoke(() =>
        {
            ConnectionDot.Fill  = connected
                ? (Brush)FindResource("SuccessBrush")
                : (Brush)FindResource("ErrorBrush");
            ConnectionText.Text = connected ? "Conectado" : "Sin conexion";
        });
    }

    // =====================
    // MODO MANTENIMIENTO
    // =====================
    private async Task CheckMaintenance()
    {
        try
        {
            var maint = await App.Api.GetMaintenanceAsync();
            Dispatcher.Invoke(() =>
            {
                if (maint?.Enabled == true)
                {
                    MaintenanceMsg.Text     = !string.IsNullOrEmpty(maint.Message)
                        ? maint.Message
                        : "Estamos realizando mejoras. Vuelva pronto.";
                    MaintenanceOverlay.Visibility = Visibility.Visible;
                }
                else
                {
                    MaintenanceOverlay.Visibility = Visibility.Collapsed;
                }
            });
        }
        catch { /* ignorar si no hay conexion */ }
    }

    protected override void OnClosed(EventArgs e)
    {
        _clockTimer.Stop();
        _statusTimer.Stop();
        _maintenanceTimer.Stop();
        base.OnClosed(e);
    }
}

// Interfaz para vistas que se pueden refrescar
public interface IRefreshable
{
    Task RefreshAsync();
}
