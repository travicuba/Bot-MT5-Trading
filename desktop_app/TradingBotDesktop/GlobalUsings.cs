// GlobalUsings.cs
// Resuelve conflictos de nombres entre WPF y WinForms
// WinForms se incluye solo para FolderBrowserDialog en SettingsView

global using Application  = System.Windows.Application;
global using Button       = System.Windows.Controls.Button;
global using Brush        = System.Windows.Media.Brush;
global using Brushes      = System.Windows.Media.Brushes;
global using Color        = System.Windows.Media.Color;
global using Image        = System.Windows.Controls.Image;
global using MenuItem     = System.Windows.Controls.MenuItem;
global using MessageBox   = System.Windows.MessageBox;
global using MessageBoxButton = System.Windows.MessageBoxButton;
global using MessageBoxImage  = System.Windows.MessageBoxImage;
global using MessageBoxResult = System.Windows.MessageBoxResult;
global using Timer        = System.Threading.Timer;
