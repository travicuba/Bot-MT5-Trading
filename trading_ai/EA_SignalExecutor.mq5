//+------------------------------------------------------------------+
//| EA_SignalExecutor.mq5 - CORREGIDO                                |
//| Se guía por bot_status.json, NO por edad de signal.json          |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>

CTrade trade;

//================ CONFIG =================//
input string Bot_Status_File = "bot_status.json";
input string Signal_File = "signals\\signal.json";
input string Feedback_File = "trade_feedback.json";
input string Market_Data_File = "market_data.json";

input double Min_Confidence = 0.30;
input int    Data_Write_Interval = 10;

// Indicadores
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
string last_signal_id = "";
string active_signal_id = "";
string active_action = "";

datetime last_data_write_time = 0;
datetime last_bot_status_check = 0;

int handle_rsi, handle_macd, handle_ema_fast, handle_ema_slow, handle_ema_long;
int handle_bb, handle_atr;

double pip_value;
long stops_level;

//================ BOT STATUS CHECK =================//
bool IsBotRunning()
{
   // Verificar cada 5 segundos
   datetime current_time = TimeCurrent();
   if(current_time - last_bot_status_check < 5)
      return true;  // Asumir que sigue corriendo
   
   last_bot_status_check = current_time;
   
   int handle = FileOpen(Bot_Status_File, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("⚠️ BOT STATUS NO DETECTADO");
      return false;
   }
   
   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);
   FileClose(handle);
   
   // Verificar si "running": true
   if(StringFind(content, "\"running\": true") < 0)
   {
      Print("🛑 BOT EN STOP (running=false)");
      return false;
   }
   
   Print("✅ BOT CORRIENDO (running=true)");
   return true;
}

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

   // Verificar señal STOP
   if(StringFind(sig.signal_id, "_STOP") >= 0)
   {
      Print("🛑 SEÑAL STOP");
      sig.action = "NONE";
      return false;
   }
   
   // Verificar señal NONE
   if(StringFind(sig.signal_id, "_NONE") >= 0)
   {
      return false;
   }
   
   // Verificar si ya procesada
   if(sig.signal_id == "" || sig.signal_id == last_signal_id)
      return false;

   // Verificar confidence
   if(sig.confidence < Min_Confidence)
   {
      Print("⚠️ Confianza baja: ", sig.confidence);
      return false;
   }

   Print("✅ SEÑAL VÁLIDA");
   Print("   ID: ", sig.signal_id);
   Print("   Action: ", sig.action);
   Print("   Confidence: ", sig.confidence);
   
   last_signal_id = sig.signal_id;
   
   return true;
}

//================ WRITE FEEDBACK =================//
void WriteTradeFeedback(string result, double pips)
{
   int handle = FileOpen(Feedback_File, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("❌ No se pudo escribir feedback");
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

   Print("📊 FEEDBACK: ", result, " | Pips: ", pips);
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
   
   Print("🔔 TRADE CERRADO: ", res, " | ", pips, " pips");
}

//================ WRITE MARKET DATA =================//
void WriteMarketData()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
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
   
   // Trend detection
   string trend = "SIDEWAYS";
   if(ema_fast_buffer[0] > ema_slow_buffer[0] && ema_slow_buffer[0] > ema_long_buffer[0])
      trend = "STRONG_UP";
   else if(ema_fast_buffer[0] > ema_slow_buffer[0])
      trend = "UP";
   else if(ema_fast_buffer[0] < ema_slow_buffer[0] && ema_slow_buffer[0] < ema_long_buffer[0])
      trend = "STRONG_DOWN";
   else if(ema_fast_buffer[0] < ema_slow_buffer[0])
      trend = "DOWN";
   
   // Volatility
   double atr_array[20];
   ArraySetAsSeries(atr_array, true);
   CopyBuffer(handle_atr, 0, 0, 20, atr_array);
   double atr_avg = 0;
   for(int i = 0; i < 20; i++)
      atr_avg += atr_array[i];
   atr_avg /= 20;
   
   string volatility = "NORMAL";
   if(atr_buffer[0] > atr_avg * 1.5)
      volatility = "HIGH";
   else if(atr_buffer[0] < atr_avg * 0.5)
      volatility = "LOW";
   
   // JSON
   string json = "{\n";
   json += "  \"symbol\": \"" + _Symbol + "\",\n";
   json += "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",\n";
   json += "  \"bid\": " + DoubleToString(bid, _Digits) + ",\n";
   json += "  \"ask\": " + DoubleToString(ask, _Digits) + ",\n";
   json += "  \"indicators\": {\n";
   json += "    \"rsi\": " + DoubleToString(rsi_buffer[0], 2) + ",\n";
   json += "    \"macd\": {\n";
   json += "      \"main\": " + DoubleToString(macd_main[0], _Digits) + ",\n";
   json += "      \"signal\": " + DoubleToString(macd_signal[0], _Digits) + "\n";
   json += "    },\n";
   json += "    \"bollinger\": {\n";
   json += "      \"upper\": " + DoubleToString(bb_upper[0], _Digits) + ",\n";
   json += "      \"middle\": " + DoubleToString(bb_middle[0], _Digits) + ",\n";
   json += "      \"lower\": " + DoubleToString(bb_lower[0], _Digits) + "\n";
   json += "    }\n";
   json += "  },\n";
   json += "  \"analysis\": {\n";
   json += "    \"trend\": \"" + trend + "\",\n";
   json += "    \"volatility\": \"" + volatility + "\"\n";
   json += "  }\n";
   json += "}\n";
   
   int handle = FileOpen(Market_Data_File, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle != INVALID_HANDLE)
   {
      FileWriteString(handle, json);
      FileClose(handle);
   }
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
      Print("❌ Error inicializando indicadores");
      return false;
   }
   
   Print("✅ Indicadores OK");
   return true;
}

//================ ON TICK =================//
void OnTick()
{
   // Escribir market data periódicamente
   datetime current_time = TimeCurrent();
   if(current_time - last_data_write_time >= Data_Write_Interval)
   {
      WriteMarketData();
      last_data_write_time = current_time;
   }
   
   // VERIFICAR BOT STATUS
   if(!IsBotRunning())
   {
      static bool logged = false;
      if(!logged)
      {
         Print("⏸️ EA EN ESPERA - Bot Python detenido");
         logged = true;
      }
      return;
   }
   static bool logged = false;
   logged = false;
   
   // No operar si hay posiciones
   if(PositionsTotal() > 0)
      return;

   // Leer señal
   Signal sig;
   if(!ReadSignal(sig))
      return;
   
   if(sig.action == "NONE")
      return;

   // Calcular pip value
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits == 5 || digits == 3)
      pip_value = 10 * _Point;
   else
      pip_value = _Point;
   
   stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);

   double lot = 0.01;
   double entry_price, sl_price, tp_price;
   
   if(sig.action == "BUY")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl_price = entry_price - (sig.sl_pips * pip_value);
      tp_price = entry_price + (sig.tp_pips * pip_value);
      
      // Ajustar stops si es necesario
      double min_distance = stops_level * _Point;
      if(stops_level > 0)
      {
         if((entry_price - sl_price) < min_distance)
            sl_price = entry_price - min_distance;
         if((tp_price - entry_price) < min_distance)
            tp_price = entry_price + min_distance;
      }
      
      Print("📈 BUY @ ", DoubleToString(entry_price, _Digits));
      Print("   SL: ", DoubleToString(sl_price, _Digits));
      Print("   TP: ", DoubleToString(tp_price, _Digits));
      
      bool ok = trade.Buy(lot, _Symbol, entry_price, sl_price, tp_price);
      
      if(ok)
      {
         active_signal_id = sig.signal_id;
         active_action = sig.action;
         Print("✅ ORDEN BUY ABIERTA");
      }
      else
      {
         Print("❌ ERROR: ", trade.ResultRetcodeDescription());
      }
   }
   else if(sig.action == "SELL")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl_price = entry_price + (sig.sl_pips * pip_value);
      tp_price = entry_price - (sig.tp_pips * pip_value);
      
      // Ajustar stops
      double min_distance = stops_level * _Point;
      if(stops_level > 0)
      {
         if((sl_price - entry_price) < min_distance)
            sl_price = entry_price + min_distance;
         if((entry_price - tp_price) < min_distance)
            tp_price = entry_price - min_distance;
      }
      
      Print("📉 SELL @ ", DoubleToString(entry_price, _Digits));
      Print("   SL: ", DoubleToString(sl_price, _Digits));
      Print("   TP: ", DoubleToString(tp_price, _Digits));
      
      bool ok = trade.Sell(lot, _Symbol, entry_price, sl_price, tp_price);
      
      if(ok)
      {
         active_signal_id = sig.signal_id;
         active_action = sig.action;
         Print("✅ ORDEN SELL ABIERTA");
      }
      else
      {
         Print("❌ ERROR: ", trade.ResultRetcodeDescription());
      }
   }
}

//================ INIT =================//
int OnInit()
{
   Print("========================================");
   Print("EA SignalExecutor v5.0 - FIXED");
   Print("Se guía por bot_status.json");
   Print("========================================");
   
   if(!InitIndicators())
   {
      Print("❌ Fallo al inicializar");
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
   
   Print("EA SignalExecutor DETENIDO");
}
