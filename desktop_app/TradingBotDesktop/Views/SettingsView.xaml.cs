using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TradingBotDesktop.Views;

public partial class SettingsView : Page, IRefreshable
{
    public SettingsView()
    {
        InitializeComponent();
        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        // Cargar desde AppSettings
        TxtVpsUrl.Text          = App.Settings.VpsUrl;
        TxtApiKey.Text          = App.Settings.ApiKey;
        TxtMt5Path.Text         = App.Settings.Mt5FilesPath;
        ChkBridgeAutoStart.IsChecked = App.Settings.BridgeAutoStart;
        ChkAutoRefresh.IsChecked     = App.Settings.AutoRefresh;
        TxtRefreshInterval.Text = App.Settings.RefreshInterval.ToString();

        // Estado mantenimiento actual
        await LoadMaintenanceStatus();
    }

    private async Task LoadMaintenanceStatus()
    {
        try
        {
            var maint = await App.Api.GetMaintenanceAsync();
            if (maint != null)
            {
                MaintenanceStatus.Text = maint.Enabled
                    ? $"MANTENIMIENTO ACTIVO desde {maint.Since ?? "-"}"
                    : "Sin mantenimiento activo";
                MaintenanceStatus.Foreground = maint.Enabled
                    ? (Brush)Application.Current.FindResource("WarningBrush")
                    : (Brush)Application.Current.FindResource("SuccessBrush");
            }
        }
        catch { /* ignorar */ }
    }

    private async void BtnTest_Click(object sender, RoutedEventArgs e)
    {
        TestResult.Text       = "Probando...";
        TestResult.Foreground = (Brush)Application.Current.FindResource("TextSecondaryBrush");

        App.Api.UpdateConnection(TxtVpsUrl.Text.Trim(), TxtApiKey.Text.Trim());
        bool ok = await App.Api.PingAsync();

        TestResult.Text       = ok ? "Conexion exitosa" : "Error: no se puede conectar";
        TestResult.Foreground = ok
            ? (Brush)Application.Current.FindResource("SuccessBrush")
            : (Brush)Application.Current.FindResource("ErrorBrush");
    }

    private void BtnBrowseMt5_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new System.Windows.Forms.FolderBrowserDialog
        {
            Description         = "Selecciona la carpeta 'Files' de MetaTrader 5",
            UseDescriptionForTitle = true,
            ShowNewFolderButton = false,
        };

        if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            TxtMt5Path.Text = dialog.SelectedPath;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        if (!int.TryParse(TxtRefreshInterval.Text, out int interval) || interval < 1)
        {
            MessageBox.Show("Intervalo de actualizacion invalido.", "Validacion",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        App.Settings.VpsUrl          = TxtVpsUrl.Text.Trim();
        App.Settings.ApiKey          = TxtApiKey.Text.Trim();
        App.Settings.Mt5FilesPath    = TxtMt5Path.Text.Trim();
        App.Settings.BridgeAutoStart = ChkBridgeAutoStart.IsChecked ?? true;
        App.Settings.AutoRefresh     = ChkAutoRefresh.IsChecked ?? true;
        App.Settings.RefreshInterval = interval;
        App.Settings.Save();

        // Actualizar servicio API con nuevas credenciales
        App.Api.UpdateConnection(App.Settings.VpsUrl, App.Settings.ApiKey);

        // Actualizar ruta puente si esta corriendo
        if (App.Bridge.IsRunning && !string.IsNullOrEmpty(App.Settings.Mt5FilesPath))
            App.Bridge.UpdateMt5Path(App.Settings.Mt5FilesPath);

        MessageBox.Show("Configuracion guardada correctamente.", "Guardado",
            MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private async void BtnMaintenanceOn_Click(object sender, RoutedEventArgs e)
    {
        var confirm = MessageBox.Show(
            "¿Activar modo mantenimiento? Los usuarios no podran usar la app.",
            "Confirmar", MessageBoxButton.YesNo, MessageBoxImage.Warning);

        if (confirm != MessageBoxResult.Yes) return;

        var msg = TxtMaintenanceMsg.Text.Trim();
        await App.Api.SetMaintenanceAsync(true, msg);
        await LoadMaintenanceStatus();

        MessageBox.Show("Modo mantenimiento activado.", "Mantenimiento",
            MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private async void BtnMaintenanceOff_Click(object sender, RoutedEventArgs e)
    {
        await App.Api.SetMaintenanceAsync(false, "");
        await LoadMaintenanceStatus();

        MessageBox.Show("Modo mantenimiento desactivado.", "Mantenimiento",
            MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
