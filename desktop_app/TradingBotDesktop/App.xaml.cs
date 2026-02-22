using System.Windows;
using TradingBotDesktop.Services;

namespace TradingBotDesktop;

public partial class App : Application
{
    public static ApiService      Api     { get; private set; } = null!;
    public static AuthService     Auth    { get; private set; } = null!;
    public static Mt5BridgeService Bridge { get; private set; } = null!;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        Auth = new AuthService();
        Auth.RestoreSession();   // Cargar token guardado

        Api    = new ApiService(AppSettings.Instance.VpsUrl, AppSettings.Instance.ApiKey);
        Bridge = new Mt5BridgeService(Api);

        if (AppSettings.Instance.BridgeAutoStart && !string.IsNullOrEmpty(AppSettings.Instance.Mt5FilesPath))
            Bridge.Start(AppSettings.Instance.Mt5FilesPath);

        // Si hay sesión guardada válida → ir directo a home
        // Si no → mostrar login
        if (Auth.IsLoggedIn)
        {
            // Verificar modo mantenimiento del servidor
            var maintenance = await ServerApiService.CheckMaintenanceAsync();
            if (maintenance.Enabled)
            {
                var mw = new MainWindow();
                mw.Show();
                mw.ShowMaintenance(maintenance.Message);
            }
            else
            {
                new MainWindow().Show();
            }
        }
        else
        {
            new LoginWindow().Show();
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Bridge.Stop();
        base.OnExit(e);
    }
}
