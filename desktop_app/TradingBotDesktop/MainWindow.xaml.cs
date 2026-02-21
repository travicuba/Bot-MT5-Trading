using System.Windows;
using System.Windows.Threading;
using TradingBotDesktop.Services;
using TradingBotDesktop.Views;

namespace TradingBotDesktop;

public partial class MainWindow : Window
{
    private readonly DispatcherTimer _clock             = new();
    private readonly DispatcherTimer _maintenanceTimer  = new();

    public MainWindow()
    {
        InitializeComponent();

        var auth = App.Auth;
        UserLabel.Text   = auth.IsLoggedIn ? $"  {auth.FullName}" : "  Usuario";
        LicenseText.Text = auth.LicenseType.ToUpper();
        LicenseBadge.BorderBrush = auth.LicenseType switch
        {
            "lifetime" => System.Windows.Media.Brushes.Gold,
            "annual"   => System.Windows.Media.Brushes.LimeGreen,
            "monthly"  => System.Windows.Media.Brushes.CornflowerBlue,
            _          => System.Windows.Media.Brushes.DimGray,
        };

        _clock.Interval = TimeSpan.FromSeconds(1);
        _clock.Tick    += (_, _) => ClockLabel.Text = DateTime.Now.ToString("HH:mm:ss");
        _clock.Start();

        _maintenanceTimer.Interval = TimeSpan.FromSeconds(30);
        _maintenanceTimer.Tick    += async (_, _) =>
        {
            var m = await ServerApiService.CheckMaintenanceAsync();
            if (m.Enabled) ShowMaintenance(m.Message);
            else           HideMaintenance();
        };
        _maintenanceTimer.Start();

        NavigateHome();

        Closed += (_, _) => { _clock.Stop(); _maintenanceTimer.Stop(); };
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    public void NavigateHome()
    {
        MainFrame.Navigate(new HomeView(this));
        BtnHome.Visibility = Visibility.Collapsed;
    }

    public void NavigateMT5()
    {
        MainFrame.Navigate(new MT5BotView(this));
        BtnHome.Visibility = Visibility.Visible;
    }

    public void NavigateBingX()
    {
        MainFrame.Navigate(new BingXBotView(this));
        BtnHome.Visibility = Visibility.Visible;
    }

    // ── Maintenance ───────────────────────────────────────────────────────────

    public void ShowMaintenance(string message)
    {
        MaintenanceMsg.Text           = message;
        MaintenanceOverlay.Visibility = Visibility.Visible;
    }

    public void HideMaintenance()
    {
        MaintenanceOverlay.Visibility = Visibility.Collapsed;
    }

    // ── Header buttons ────────────────────────────────────────────────────────

    private void BtnHome_Click(object sender, RoutedEventArgs e) => NavigateHome();

    private void BtnSettings_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show("Accede a la configuración desde la pestaña correspondiente de cada bot.",
                        "Configuración", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void BtnLogout_Click(object sender, RoutedEventArgs e)
    {
        var r = MessageBox.Show("¿Deseas cerrar sesión?", "Confirmar",
                                MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (r != MessageBoxResult.Yes) return;
        _clock.Stop();
        _maintenanceTimer.Stop();
        App.Auth.Logout();
        new LoginWindow().Show();
        Close();
    }

    // ── Footer status ─────────────────────────────────────────────────────────

    public void SetMt5Status(bool online) =>
        Mt5StatusDot.Fill = new System.Windows.Media.SolidColorBrush(
            online
                ? System.Windows.Media.Color.FromRgb(0x06, 0xFF, 0xA5)
                : System.Windows.Media.Color.FromRgb(0x55, 0x55, 0x55));

    public void SetBingXStatus(bool online) =>
        BingXStatusDot.Fill = new System.Windows.Media.SolidColorBrush(
            online
                ? System.Windows.Media.Color.FromRgb(0xFF, 0x9A, 0x00)
                : System.Windows.Media.Color.FromRgb(0x55, 0x55, 0x55));
}
