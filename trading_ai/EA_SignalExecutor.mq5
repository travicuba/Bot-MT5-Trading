//+------------------------------------------------------------------+
//| Signal Executor EA + Trade Feedback + Market Data Writer        |
//| VERSION CORREGIDA - Sin errores de compilación                  |
//+------------------------------------------------------------------+
#property strict
#property tester_file "signals\\signal.json"

#include <Trade/Trade.mqh>
#include <Files\FileTxt.mqh>

CTrade trade;

//================ CONFIG =================//
input string Signal_File   = "signals\\signal.json";
input string Feedback_File = "trade_feedback.json";
input double Min_Confidence = 0.70;

// ======== CONFIG PARA MARKET DATA ========//
input string Market_Data_File = "market_data.json";
input int    Data_Write_Interval = 10;
input int    RSI_Period = 14;
input int    MACD_Fast = 12;
input int    MACD_Slow = 26;
input int    MACD_Signal = 9;
input int    EMA_Fast = 20;
input int    EMA_Slow = 50;
input int    EMA_Long = 200;
input int    BB_Period = 20;
input double BB_Deviation = 2.0;
input int    ATR_Period = 14;

//================ STRUCT =================//
struct Signal
{
   string signal_id;
   string action;
   double confidence;
   double sl_pips;
   double tp_pips;
};

//================ GLOBAL =================//
string last_signal_id   = "";
string active_signal_id = "";
string active_action    = "";

datetime last_data_write_time = 0;
int handle_rsi, handle_macd, handle_ema_fast, handle_ema_slow, handle_ema_long;
int handle_bb, handle_atr;

double pip_value;
long stops_level;  // CAMBIADO: de int a long

//================ JSON HELPER =================//
string GetJSONValue(string json, string key)
{
   int pos = StringFind(json, "\"" + key + "\":");
   if(pos < 0) return "";

   pos += StringLen(key) + 3;

   while(
      StringGetCharacter(json, pos) == ' ' ||
      StringGetCharacter(json, pos) == '\"'
   )
      pos++;

   string value = "";
   while(pos < StringLen(json))
   {
      ushort c = StringGetCharacter(json, pos);
      if(c == ',' || c == '}' || c == '\"')
         break;

      value += CharToString(c);
      pos++;
   }
   return value;
}

//================ READ SIGNAL =================//
bool ReadSignal(Signal &sig)
{
   int handle = FileOpen(Signal_File, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("No se pudo abrir signal.json | Error: ", GetLastError());
      return false;
   }

   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);

   FileClose(handle);

   if(StringLen(content) == 0)
      return false;

   sig.signal_id  = GetJSONValue(content, "signal_id");

   sig.action     = StringFind(content, "\"action\": \"BUY\"")  >= 0 ? "BUY" :
                    StringFind(content, "\"action\": \"SELL\"") >= 0 ? "SELL" : "NONE";

   sig.confidence = StringToDouble(GetJSONValue(content, "confidence"));
   sig.sl_pips    = StringToDouble(GetJSONValue(content, "sl_pips"));
   sig.tp_pips    = StringToDouble(GetJSONValue(content, "tp_pips"));

   if(sig.signal_id == "" || sig.signal_id == last_signal_id)
      return false;

   if(sig.confidence < Min_Confidence)
      return false;

   last_signal_id = sig.signal_id;
   return true;
}

//================ WRITE FEEDBACK =================//
void WriteTradeFeedback(string result, double pips)
{
   int handle = FileOpen(Feedback_File, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("No se pudo escribir trade_feedback.json");
      return;
   }

   string json =
      "{\n"
      "  \"signal_id\": \"" + active_signal_id + "\",\n"
      "  \"result\": \"" + result + "\",\n"
      "  \"pips\": " + DoubleToString(pips, 2) + ",\n"
      "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"\n"
      "}";

   FileWriteString(handle, json);
   FileClose(handle);

   Print("FEEDBACK GUARDADO -> ", result, " | Pips: ", pips);
}

//================ ON TRADE TRANSACTION =================//
void OnTradeTransaction(
   const MqlTradeTransaction &trans,
   const MqlTradeRequest &request,
   const MqlTradeResult &result
)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
      
   ulong deal_ticket = trans.deal;
   if(!HistoryDealSelect(deal_ticket))
      return;
      
   if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY) != DEAL_ENTRY_OUT)
      return;
      
   double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
   double pips = profit / 10.0;
   
   string res = pips >= 0 ? "WIN" : "LOSS";
   
   WriteTradeFeedback(res, pips);
   
   active_signal_id = "";
   active_action = "";
   
   Print("TRADE CERRADO -> ", res, " | Pips: ", pips);
}

//================ DETECT TREND =================//
string DetectTrend(double ema_fast, double ema_slow, double ema_long, double current_price)
{
   if(ema_fast > ema_slow && ema_slow > ema_long && current_price > ema_fast)
      return "STRONG_UP";
   
   if(ema_fast > ema_slow && current_price > ema_fast)
      return "UP";
   
   if(ema_fast < ema_slow && ema_slow < ema_long && current_price < ema_fast)
      return "STRONG_DOWN";
   
   if(ema_fast < ema_slow && current_price < ema_fast)
      return "DOWN";
   
   return "SIDEWAYS";
}

//================ DETECT VOLATILITY =================//
string DetectVolatility(double atr, double atr_avg)
{
   if(atr > atr_avg * 1.5)
      return "HIGH";
   else if(atr < atr_avg * 0.5)
      return "LOW";
   else
      return "NORMAL";
}

//================ GET CANDLES DATA =================//
string GetCandlesJSON(int count)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, count, rates);
   if(copied <= 0)
      return "[]";
   
   string json = "[\n";
   
   for(int i = 0; i < copied; i++)
   {
      json += "    {\n";
      json += "      \"time\": \"" + TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS) + "\",\n";
      json += "      \"open\": " + DoubleToString(rates[i].open, _Digits) + ",\n";
      json += "      \"high\": " + DoubleToString(rates[i].high, _Digits) + ",\n";
      json += "      \"low\": " + DoubleToString(rates[i].low, _Digits) + ",\n";
      json += "      \"close\": " + DoubleToString(rates[i].close, _Digits) + ",\n";
      json += "      \"volume\": " + IntegerToString(rates[i].tick_volume) + "\n";
      json += "    }";
      
      if(i < copied - 1)
         json += ",\n";
      else
         json += "\n";
   }
   
   json += "  ]";
   return json;
}

//================ WRITE MARKET DATA =================//
void WriteMarketData()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spread = (ask - bid) / _Point;
   
   double rsi_buffer[], macd_main[], macd_signal[], ema_fast_buffer[], ema_slow_buffer[], ema_long_buffer[];
   double bb_upper[], bb_middle[], bb_lower[], atr_buffer[];
   
   ArraySetAsSeries(rsi_buffer, true);
   ArraySetAsSeries(macd_main, true);
   ArraySetAsSeries(macd_signal, true);
   ArraySetAsSeries(ema_fast_buffer, true);
   ArraySetAsSeries(ema_slow_buffer, true);
   ArraySetAsSeries(ema_long_buffer, true);
   ArraySetAsSeries(bb_upper, true);
   ArraySetAsSeries(bb_middle, true);
   ArraySetAsSeries(bb_lower, true);
   ArraySetAsSeries(atr_buffer, true);
   
   if(CopyBuffer(handle_rsi, 0, 0, 1, rsi_buffer) <= 0) return;
   if(CopyBuffer(handle_macd, 0, 0, 1, macd_main) <= 0) return;
   if(CopyBuffer(handle_macd, 1, 0, 1, macd_signal) <= 0) return;
   if(CopyBuffer(handle_ema_fast, 0, 0, 1, ema_fast_buffer) <= 0) return;
   if(CopyBuffer(handle_ema_slow, 0, 0, 1, ema_slow_buffer) <= 0) return;
   if(CopyBuffer(handle_ema_long, 0, 0, 1, ema_long_buffer) <= 0) return;
   if(CopyBuffer(handle_bb, 0, 0, 1, bb_upper) <= 0) return;
   if(CopyBuffer(handle_bb, 1, 0, 1, bb_middle) <= 0) return;
   if(CopyBuffer(handle_bb, 2, 0, 1, bb_lower) <= 0) return;
   if(CopyBuffer(handle_atr, 0, 0, 1, atr_buffer) <= 0) return;
   
   double atr_array[20];
   ArraySetAsSeries(atr_array, true);
   CopyBuffer(handle_atr, 0, 0, 20, atr_array);
   double atr_avg = 0;
   for(int i = 0; i < 20; i++)
      atr_avg += atr_array[i];
   atr_avg /= 20;
   
   string trend = DetectTrend(ema_fast_buffer[0], ema_slow_buffer[0], ema_long_buffer[0], bid);
   string volatility = DetectVolatility(atr_buffer[0], atr_avg);
   string candles = GetCandlesJSON(20);
   
   string json = "{\n";
   json += "  \"symbol\": \"" + _Symbol + "\",\n";
   json += "  \"timeframe\": \"" + EnumToString(PERIOD_CURRENT) + "\",\n";
   json += "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",\n";
   json += "  \"bid\": " + DoubleToString(bid, _Digits) + ",\n";
   json += "  \"ask\": " + DoubleToString(ask, _Digits) + ",\n";
   json += "  \"spread\": " + DoubleToString(spread, 1) + ",\n";
   json += "  \"indicators\": {\n";
   json += "    \"rsi\": " + DoubleToString(rsi_buffer[0], 2) + ",\n";
   json += "    \"macd\": {\n";
   json += "      \"main\": " + DoubleToString(macd_main[0], _Digits) + ",\n";
   json += "      \"signal\": " + DoubleToString(macd_signal[0], _Digits) + ",\n";
   json += "      \"histogram\": " + DoubleToString(macd_main[0] - macd_signal[0], _Digits) + "\n";
   json += "    },\n";
   json += "    \"ema\": {\n";
   json += "      \"fast\": " + DoubleToString(ema_fast_buffer[0], _Digits) + ",\n";
   json += "      \"slow\": " + DoubleToString(ema_slow_buffer[0], _Digits) + ",\n";
   json += "      \"long\": " + DoubleToString(ema_long_buffer[0], _Digits) + "\n";
   json += "    },\n";
   json += "    \"bollinger\": {\n";
   json += "      \"upper\": " + DoubleToString(bb_upper[0], _Digits) + ",\n";
   json += "      \"middle\": " + DoubleToString(bb_middle[0], _Digits) + ",\n";
   json += "      \"lower\": " + DoubleToString(bb_lower[0], _Digits) + "\n";
   json += "    },\n";
   json += "    \"atr\": " + DoubleToString(atr_buffer[0], _Digits) + "\n";
   json += "  },\n";
   json += "  \"analysis\": {\n";
   json += "    \"trend\": \"" + trend + "\",\n";
   json += "    \"volatility\": \"" + volatility + "\",\n";
   json += "    \"rsi_signal\": \"" + (rsi_buffer[0] > 70 ? "OVERBOUGHT" : rsi_buffer[0] < 30 ? "OVERSOLD" : "NEUTRAL") + "\",\n";
   json += "    \"macd_signal\": \"" + (macd_main[0] > macd_signal[0] ? "BULLISH" : "BEARISH") + "\"\n";
   json += "  },\n";
   json += "  \"candles\": " + candles + "\n";
   json += "}\n";
   
   int handle = FileOpen(Market_Data_File, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("No se pudo escribir market_data.json | Error: ", GetLastError());
      return;
   }
   
   FileWriteString(handle, json);
   FileClose(handle);
   
   Print("MARKET DATA actualizado -> Trend: ", trend, " | RSI: ", DoubleToString(rsi_buffer[0], 2));
}

//================ INIT INDICATORS =================//
bool InitIndicators()
{
   handle_rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   handle_macd = iMACD(_Symbol, PERIOD_CURRENT, MACD_Fast, MACD_Slow, MACD_Signal, PRICE_CLOSE);
   handle_ema_fast = iMA(_Symbol, PERIOD_CURRENT, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   handle_ema_slow = iMA(_Symbol, PERIOD_CURRENT, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   handle_ema_long = iMA(_Symbol, PERIOD_CURRENT, EMA_Long, 0, MODE_EMA, PRICE_CLOSE);
   handle_bb = iBands(_Symbol, PERIOD_CURRENT, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
   handle_atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   
   if(handle_rsi == INVALID_HANDLE || handle_macd == INVALID_HANDLE || 
      handle_ema_fast == INVALID_HANDLE || handle_ema_slow == INVALID_HANDLE ||
      handle_ema_long == INVALID_HANDLE || handle_bb == INVALID_HANDLE ||
      handle_atr == INVALID_HANDLE)
   {
      Print("Error inicializando indicadores");
      return false;
   }
   
   Print("Indicadores inicializados correctamente");
   return true;
}

//================ CALCULATE PIP VALUE =================//
void CalculatePipValue()
{
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   
   if(digits == 5 || digits == 3)
      pip_value = 10 * _Point;
   else
      pip_value = _Point;
   
   stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   
   Print("Pip Value: ", pip_value);
   Print("Stops Level: ", stops_level, " points");
   Print("Digits: ", digits);
}

//================ ADJUST STOPS =================//
void AdjustStops(double &sl, double &tp, string action, double entry_price)
{
   double min_distance = stops_level * _Point;
   
   if(stops_level > 0)
   {
      if(action == "BUY")
      {
         double sl_distance = entry_price - sl;
         double tp_distance = tp - entry_price;
         
         if(sl_distance < min_distance)
         {
            sl = entry_price - min_distance;
            Print("SL ajustado por stops level: ", DoubleToString(sl, _Digits));
         }
         
         if(tp_distance < min_distance)
         {
            tp = entry_price + min_distance;
            Print("TP ajustado por stops level: ", DoubleToString(tp, _Digits));
         }
      }
      else if(action == "SELL")
      {
         double sl_distance = sl - entry_price;
         double tp_distance = entry_price - tp;
         
         if(sl_distance < min_distance)
         {
            sl = entry_price + min_distance;
            Print("SL ajustado por stops level: ", DoubleToString(sl, _Digits));
         }
         
         if(tp_distance < min_distance)
         {
            tp = entry_price - min_distance;
            Print("TP ajustado por stops level: ", DoubleToString(tp, _Digits));
         }
      }
   }
}

//================ ON TICK =================//
void OnTick()
{
   datetime current_time = TimeCurrent();
   if(current_time - last_data_write_time >= Data_Write_Interval)
   {
      WriteMarketData();
      last_data_write_time = current_time;
   }
   
   if(PositionsTotal() > 0)
      return;

   Signal sig;
   if(!ReadSignal(sig))
      return;

   double lot = 0.01;
   double entry_price, sl_price, tp_price;
   
   if(sig.action == "BUY")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl_price = entry_price - (sig.sl_pips * pip_value);
      tp_price = entry_price + (sig.tp_pips * pip_value);
      
      AdjustStops(sl_price, tp_price, "BUY", entry_price);
      
      Print("BUY calculado:");
      Print("   Entry: ", DoubleToString(entry_price, _Digits));
      Print("   SL: ", DoubleToString(sl_price, _Digits), " (", sig.sl_pips, " pips)");
      Print("   TP: ", DoubleToString(tp_price, _Digits), " (", sig.tp_pips, " pips)");
      
      bool ok = trade.Buy(lot, _Symbol, entry_price, sl_price, tp_price);
      
      if(ok)
      {
         active_signal_id = sig.signal_id;
         active_action = sig.action;
         Print("ORDEN BUY ABIERTA | Signal ID: ", sig.signal_id);
      }
      else
      {
         Print("ERROR abriendo BUY: ", trade.ResultRetcodeDescription());
      }
   }
   else if(sig.action == "SELL")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl_price = entry_price + (sig.sl_pips * pip_value);
      tp_price = entry_price - (sig.tp_pips * pip_value);
      
      AdjustStops(sl_price, tp_price, "SELL", entry_price);
      
      Print("SELL calculado:");
      Print("   Entry: ", DoubleToString(entry_price, _Digits));
      Print("   SL: ", DoubleToString(sl_price, _Digits), " (", sig.sl_pips, " pips)");
      Print("   TP: ", DoubleToString(tp_price, _Digits), " (", sig.tp_pips, " pips)");
      
      bool ok = trade.Sell(lot, _Symbol, entry_price, sl_price, tp_price);
      
      if(ok)
      {
         active_signal_id = sig.signal_id;
         active_action = sig.action;
         Print("ORDEN SELL ABIERTA | Signal ID: ", sig.signal_id);
      }
      else
      {
         Print("ERROR abriendo SELL: ", trade.ResultRetcodeDescription());
      }
   }
}

//================ INIT =================//
int OnInit()
{
   Print("EA SignalExecutor + Feedback + Market Data Writer INICIADO");
   
   CalculatePipValue();
   
   if(!InitIndicators())
   {
      Print("Fallo al inicializar indicadores. EA detenido.");
      return INIT_FAILED;
   }
   
   WriteMarketData();
   last_data_write_time = TimeCurrent();
   
   return INIT_SUCCEEDED;
}

//================ DEINIT =================//
void OnDeinit(const int reason)
{
   if(handle_rsi != INVALID_HANDLE) IndicatorRelease(handle_rsi);
   if(handle_macd != INVALID_HANDLE) IndicatorRelease(handle_macd);
   if(handle_ema_fast != INVALID_HANDLE) IndicatorRelease(handle_ema_fast);
   if(handle_ema_slow != INVALID_HANDLE) IndicatorRelease(handle_ema_slow);
   if(handle_ema_long != INVALID_HANDLE) IndicatorRelease(handle_ema_long);
   if(handle_bb != INVALID_HANDLE) IndicatorRelease(handle_bb);
   if(handle_atr != INVALID_HANDLE) IndicatorRelease(handle_atr);
   
   Print("EA SignalExecutor + Market Data Writer DETENIDO");
}
