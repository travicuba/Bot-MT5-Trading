using System.Windows;
using System.Windows.Threading;
using TradingBotDesktop.Services;

namespace TradingBotDesktop;

public partial class LoginWindow : Window
{
    private readonly DispatcherTimer _msgTimer = new();
    private readonly string[] _messages =
    {
        "🤖 Señales de IA para MT5 y BingX",
        "📊 El sistema aprende de cada operación",
        "☁  Tus datos seguros en la nube",
        "⚡ Ejecución en tiempo real",
        "🔒 Multi-plataforma profesional",
        "💡 Panel de análisis IA en tiempo real",
        "🎯 Estrategias adaptativas con ML",
    };
    private int _msgIndex = 0;

    public LoginWindow()
    {
        InitializeComponent();

        // Cargar URL guardada
        ServerUrlBox.Text = AppSettings.Instance.ServerUrl;

        // Rotating commercial messages
        CommercialMsg.Text = _messages[0];
        _msgTimer.Interval = TimeSpan.FromSeconds(3);
        _msgTimer.Tick += (_, _) =>
        {
            _msgIndex = (_msgIndex + 1) % _messages.Length;
            CommercialMsg.Text = _messages[_msgIndex];
        };
        _msgTimer.Start();

        // Drag window
        MouseDown += (_, e) => { if (e.LeftButton == System.Windows.Input.MouseButtonState.Pressed) DragMove(); };
    }

    // ── Show/hide panels ──────────────────────────────────────────────────────

    private void ShowRegister_Click(object sender, RoutedEventArgs e)
    {
        LoginPanel.Visibility    = Visibility.Collapsed;
        RegisterPanel.Visibility = Visibility.Visible;
    }

    private void ShowLogin_Click(object sender, RoutedEventArgs e)
    {
        RegisterPanel.Visibility = Visibility.Collapsed;
        LoginPanel.Visibility    = Visibility.Visible;
    }

    private void Close_Click(object sender, RoutedEventArgs e) => Application.Current.Shutdown();

    // ── LOGIN ─────────────────────────────────────────────────────────────────

    private async void Login_Click(object sender, RoutedEventArgs e)
    {
        LoginError.Visibility = Visibility.Collapsed;
        LoginBtn.IsEnabled    = false;
        LoginBtn.Content      = "Conectando...";

        try
        {
            SaveServerUrl();
            var result = await App.Auth.LoginAsync(LoginEmail.Text.Trim(), LoginPassword.Password);
            if (result.Success)
            {
                _msgTimer.Stop();
                var main = new MainWindow();
                main.Show();
                Close();
            }
            else
            {
                ShowLoginError(result.ErrorMessage ?? "Error de inicio de sesión");
            }
        }
        catch (Exception ex)
        {
            ShowLoginError($"Error de conexión: {ex.Message}");
        }
        finally
        {
            LoginBtn.IsEnabled = true;
            LoginBtn.Content   = "INICIAR SESIÓN";
        }
    }

    // ── REGISTER ─────────────────────────────────────────────────────────────

    private async void Register_Click(object sender, RoutedEventArgs e)
    {
        RegError.Visibility  = Visibility.Collapsed;
        RegisterBtn.IsEnabled = false;
        RegisterBtn.Content   = "Creando cuenta...";

        try
        {
            SaveServerUrl();
            var result = await App.Auth.RegisterAsync(
                RegFirstName.Text.Trim(),
                RegLastName.Text.Trim(),
                RegEmail.Text.Trim(),
                RegPassword.Password);

            if (result.Success)
            {
                _msgTimer.Stop();
                var main = new MainWindow();
                main.Show();
                Close();
            }
            else
            {
                ShowRegError(result.ErrorMessage ?? "Error al registrar");
            }
        }
        catch (Exception ex)
        {
            ShowRegError($"Error de conexión: {ex.Message}");
        }
        finally
        {
            RegisterBtn.IsEnabled = true;
            RegisterBtn.Content   = "CREAR CUENTA";
        }
    }

    private void ShowLoginError(string msg)
    {
        LoginError.Text       = msg;
        LoginError.Visibility = Visibility.Visible;
    }

    private void ShowRegError(string msg)
    {
        RegError.Text       = msg;
        RegError.Visibility = Visibility.Visible;
    }

    private void SaveServerUrl()
    {
        var url = ServerUrlBox.Text.Trim();
        if (!string.IsNullOrEmpty(url))
        {
            AppSettings.Instance.ServerUrl = url;
            AppSettings.Instance.Save();
        }
    }
}
