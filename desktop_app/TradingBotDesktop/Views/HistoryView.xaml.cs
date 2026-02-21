using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using TradingBotDesktop.Models;

namespace TradingBotDesktop.Views;

public partial class HistoryView : Page, IRefreshable
{
    private List<TradeRecord> _allTrades = new();

    public HistoryView()
    {
        InitializeComponent();
        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        try
        {
            int limit = int.TryParse((FilterLimit.SelectedItem as ComboBoxItem)?.Content?.ToString(), out int l)
                ? l : 50;

            var resp = await App.Api.GetHistoryAsync(limit);
            if (resp == null) return;

            _allTrades = resp.Trades;
            Dispatcher.Invoke(() =>
            {
                TotalCount.Text = $"{resp.Total} trades en total";
                ApplyFilter();
            });
        }
        catch { /* ignorar */ }
    }

    private void ApplyFilter()
    {
        var filter = (FilterResult.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "Todos";

        var filtered = filter == "Todos"
            ? _allTrades
            : _allTrades.Where(t => t.Result == filter).ToList();

        HistoryGrid.ItemsSource = filtered;
    }

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
        => await RefreshAsync();

    private async void Filter_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_allTrades.Count == 0)
            await RefreshAsync();
        else
            ApplyFilter();
    }

    private void BtnExport_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                FileName   = $"historial_{DateTime.Now:yyyyMMdd}",
                DefaultExt = ".csv",
                Filter     = "CSV files (*.csv)|*.csv",
            };
            if (dialog.ShowDialog() != true) return;

            var sb = new StringBuilder();
            sb.AppendLine("Fecha,Estrategia,Simbolo,Accion,Resultado,Pips");

            foreach (var t in _allTrades)
                sb.AppendLine($"{t.Timestamp},{t.SetupName},{t.Symbol},{t.Action},{t.Result},{t.Pips:F1}");

            File.WriteAllText(dialog.FileName, sb.ToString(), Encoding.UTF8);
            MessageBox.Show($"Exportado: {dialog.FileName}", "Exportado",
                MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error al exportar: {ex.Message}", "Error",
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
