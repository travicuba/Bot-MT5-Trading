using System.Windows;
using TradingBotDesktop.Services;

namespace TradingBotDesktop;

public partial class App : Application
{
    public static ApiService    Api     { get; private set; } = null!;
    public static AppSettings   Settings { get; private set; } = null!;
    public static Mt5BridgeService Bridge { get; private set; } = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        Settings = new AppSettings();
        Settings.Load();

        Api = new ApiService(Settings.VpsUrl, Settings.ApiKey);

        Bridge = new Mt5BridgeService(Api);

        if (Settings.BridgeAutoStart && !string.IsNullOrEmpty(Settings.Mt5FilesPath))
            Bridge.Start(Settings.Mt5FilesPath);
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Bridge.Stop();
        base.OnExit(e);
    }
}
