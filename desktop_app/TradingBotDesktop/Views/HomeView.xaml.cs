using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TradingBotDesktop.Services;

namespace TradingBotDesktop.Views;

public partial class HomeView : Page
{
    private readonly MainWindow _main;

    public HomeView(MainWindow main)
    {
        InitializeComponent();
        _main = main;
        Loaded += (_, _) => _ = LoadStatusAsync();
    }

    private async Task LoadStatusAsync()
    {
        try
        {
            var status = await App.Api.GetBotStatusAsync();
            bool running = status.ValueKind != System.Text.Json.JsonValueKind.Undefined
                           && status.TryGetProperty("running", out var r) && r.GetBoolean();
            SetMt5Status(running, "—");
            _main.SetMt5Status(running);
        }
        catch { }
    }

    private void SetMt5Status(bool running, string balance)
    {
        var color = running
            ? System.Windows.Media.Color.FromRgb(0x06, 0xFF, 0xA5)
            : System.Windows.Media.Color.FromRgb(0x55, 0x55, 0x55);
        Mt5Dot.Fill          = new System.Windows.Media.SolidColorBrush(color);
        Mt5StatusDot2.Fill   = new System.Windows.Media.SolidColorBrush(color);
        Mt5StatusText.Text   = running ? "Activo" : "Detenido";
        Mt5Balance.Text      = balance;
    }

    // ── Card navigation ───────────────────────────────────────────────────────

    private void Mt5Card_Click(object sender, MouseButtonEventArgs e) => _main.NavigateMT5();
    private void BingXCard_Click(object sender, MouseButtonEventArgs e) => _main.NavigateBingX();
    private void BtnMT5_Click(object sender, RoutedEventArgs e)   => _main.NavigateMT5();
    private void BtnBingX_Click(object sender, RoutedEventArgs e) => _main.NavigateBingX();
}
