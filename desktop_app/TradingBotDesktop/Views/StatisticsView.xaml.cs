using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TradingBotDesktop.Views;

public class SetupRow
{
    public string Name           { get; set; } = "";
    public int    Trades         { get; set; }
    public int    Wins           { get; set; }
    public int    Losses         { get; set; }
    public double Pips           { get; set; }
    public string WinRateDisplay => Trades > 0 ? $"{(Wins / (double)Trades * 100):F1}%" : "-";
    public string PipsDisplay    => Pips.ToString("F1");
}

public partial class StatisticsView : Page, IRefreshable
{
    public StatisticsView()
    {
        InitializeComponent();
        Loaded += async (_, _) => await RefreshAsync();
    }

    public async Task RefreshAsync()
    {
        try
        {
            var stats = await App.Api.GetStatsAsync();
            if (stats == null) return;

            Dispatcher.Invoke(() =>
            {
                // Resumen global
                StTotalTrades.Text = stats.TotalTrades.ToString();
                StWinRate.Text     = $"{stats.WinRate:F1}%";
                StTotalPips.Text   = stats.TotalPips.ToString("F1");
                StWinsLosses.Text  = $"{stats.Wins} / {stats.Losses}";

                StTotalPips.Foreground = stats.TotalPips >= 0
                    ? (Brush)Application.Current.FindResource("SuccessBrush")
                    : (Brush)Application.Current.FindResource("ErrorBrush");

                // Hoy
                TodTrades.Text  = stats.Today.Trades.ToString();
                TodWinRate.Text = $"{stats.Today.WinRate:F0}%";
                TodPips.Text    = stats.Today.Pips.ToString("F1");
                TodPips.Foreground = stats.Today.Pips >= 0
                    ? (Brush)Application.Current.FindResource("SuccessBrush")
                    : (Brush)Application.Current.FindResource("ErrorBrush");

                // Semana
                WkTrades.Text  = stats.Week.Trades.ToString();
                WkWinRate.Text = $"{stats.Week.WinRate:F0}%";
                WkPips.Text    = stats.Week.Pips.ToString("F1");
                WkPips.Foreground = stats.Week.Pips >= 0
                    ? (Brush)Application.Current.FindResource("SuccessBrush")
                    : (Brush)Application.Current.FindResource("ErrorBrush");

                // Por estrategia
                var rows = new List<SetupRow>();
                if (stats.SetupStats != null)
                {
                    foreach (var kvp in stats.SetupStats)
                    {
                        rows.Add(new SetupRow
                        {
                            Name   = kvp.Key,
                            Trades = kvp.Value.Total,
                            Wins   = kvp.Value.Wins,
                            Losses = kvp.Value.Losses,
                            Pips   = kvp.Value.Pips,
                        });
                    }
                }
                SetupGrid.ItemsSource = rows;
            });
        }
        catch { /* ignorar */ }
    }

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
        => await RefreshAsync();
}
