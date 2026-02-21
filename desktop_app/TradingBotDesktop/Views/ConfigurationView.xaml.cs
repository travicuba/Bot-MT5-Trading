using System.Windows;
using System.Windows.Controls;
using TradingBotDesktop.Models;

namespace TradingBotDesktop.Views;

public partial class ConfigurationView : Page, IRefreshable
{
    private BotConfig? _current;

    public ConfigurationView()
    {
        InitializeComponent();
        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        _current = await App.Api.GetConfigAsync();
        if (_current == null) return;

        Dispatcher.Invoke(() =>
        {
            TxtMinConf.Text       = _current.MinConfidence.ToString();
            TxtLotSize.Text       = _current.LotSize.ToString("F2");
            TxtCooldown.Text      = _current.Cooldown.ToString();
            TxtMaxDaily.Text      = _current.MaxDailyTrades.ToString();
            TxtMaxLosses.Text     = _current.MaxLosses.ToString();
            TxtMaxConcurrent.Text = _current.MaxConcurrentTrades.ToString();
            TxtMinInterval.Text   = _current.MinSignalInterval.ToString();
            TxtStartHour.Text     = _current.StartHour;
            TxtEndHour.Text       = _current.EndHour;
            ChkAvoidRepeat.IsChecked   = _current.AvoidRepeatStrategy;
            ChkAutoOptimize.IsChecked  = _current.AutoOptimize;
            StatusMsg.Text = "";
        });
    }

    private async void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        if (!ValidateForm(out string err))
        {
            MessageBox.Show(err, "Validacion", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var update = new
        {
            min_confidence        = int.Parse(TxtMinConf.Text),
            lot_size              = double.Parse(TxtLotSize.Text),
            cooldown              = int.Parse(TxtCooldown.Text),
            max_daily_trades      = int.Parse(TxtMaxDaily.Text),
            max_losses            = int.Parse(TxtMaxLosses.Text),
            max_concurrent_trades = int.Parse(TxtMaxConcurrent.Text),
            min_signal_interval   = int.Parse(TxtMinInterval.Text),
            start_hour            = TxtStartHour.Text.Trim(),
            end_hour              = TxtEndHour.Text.Trim(),
            avoid_repeat_strategy = ChkAvoidRepeat.IsChecked ?? true,
            auto_optimize         = ChkAutoOptimize.IsChecked ?? true,
        };

        bool ok = await App.Api.UpdateConfigAsync(update);
        if (ok)
        {
            StatusMsg.Text = $"Configuracion guardada - {DateTime.Now:HH:mm:ss}";
        }
        else
        {
            MessageBox.Show("Error al guardar la configuracion. Verifique la conexion VPS.",
                "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void BtnReload_Click(object sender, RoutedEventArgs e)
        => await RefreshAsync();

    private bool ValidateForm(out string error)
    {
        error = "";

        if (!int.TryParse(TxtMinConf.Text, out int conf) || conf < 0 || conf > 100)
        { error = "Confianza minima debe ser 0-100"; return false; }

        if (!double.TryParse(TxtLotSize.Text, out double lot) || lot <= 0)
        { error = "Lote debe ser mayor que 0"; return false; }

        if (!int.TryParse(TxtCooldown.Text, out int cd) || cd < 0)
        { error = "Cooldown debe ser >= 0"; return false; }

        if (!int.TryParse(TxtMaxDaily.Text, out int md) || md < 1)
        { error = "Max trades diarios debe ser >= 1"; return false; }

        if (!int.TryParse(TxtMaxLosses.Text, out int ml) || ml < 1)
        { error = "Max perdidas debe ser >= 1"; return false; }

        return true;
    }
}
