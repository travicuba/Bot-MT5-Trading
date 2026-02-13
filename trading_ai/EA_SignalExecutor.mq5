//+------------------------------------------------------------------+
//| EA_SignalExecutor.mq5 v6.0 - MULTI-TRADE + FEEDBACK QUEUE       |
//| Soporta multiples operaciones simultaneas                        |
//| Feedback por archivos individuales (no se pierden cierres masivos)|
//| Borra signal.json despues de leer para evitar re-lecturas        |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>

CTrade trade;

//================ CONFIG =================//
input string Bot_Status_File = "bot_status.json";
input string Signal_File = "signals\\signal.json";
input string Feedback_Folder = "trade_feedback\\";
input string Market_Data_File = "market_data.json";

input double Min_Confidence = 0.30;
input int    Data_Write_Interval = 10;
input int    Max_Concurrent_Default = 3;

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
   double lot_size;
};

//================ MULTI-TRADE TRACKING =================//
#define MAX_TRACKED_TRADES 20

string tracked_signal_ids[MAX_TRACKED_TRADES];
ulong  tracked_position_ids[MAX_TRACKED_TRADES];
int    tracked_count = 0;

// Pending signal - se asigna antes de abrir trade, se mapea en OnTradeTransaction
string pending_signal_id = "";

//================ GLOBAL =================//
string last_signal_id = "";

datetime last_data_write_time = 0;
datetime last_bot_status_check = 0;

double synced_min_confidence = 0.30;
int    synced_max_concurrent = 3;
double synced_lot_size = 0.01;

int handle_rsi, handle_macd, handle_ema_fast, handle_ema_slow, handle_ema_long;
int handle_bb, handle_atr;

double pip_value;
long stops_level;

//================ TRADE TRACKING FUNCTIONS =================//
void AddTradeMapping(ulong position_id, string signal_id)
{
   if(tracked_count >= MAX_TRACKED_TRADES)
   {
      Print("WARNING: Max tracked trades reached, removing oldest");
      // Shift array left
      for(int i = 0; i < tracked_count - 1; i++)
      {
         tracked_signal_ids[i] = tracked_signal_ids[i + 1];
         tracked_position_ids[i] = tracked_position_ids[i + 1];
      }
      tracked_count--;
   }

   tracked_signal_ids[tracked_count] = signal_id;
   tracked_position_ids[tracked_count] = position_id;
   tracked_count++;

   Print("TRACKING: Posicion ", position_id, " -> ", signal_id, " (total: ", tracked_count, ")");
}

string FindAndRemoveSignalId(ulong position_id)
{
   for(int i = 0; i < tracked_count; i++)
   {
      if(tracked_position_ids[i] == position_id)
      {
         string sig_id = tracked_signal_ids[i];

         // Shift remaining elements left
         for(int j = i; j < tracked_count - 1; j++)
         {
            tracked_signal_ids[j] = tracked_signal_ids[j + 1];
            tracked_position_ids[j] = tracked_position_ids[j + 1];
         }
         tracked_count--;

         Print("UNTRACK: Posicion ", position_id, " era ", sig_id, " (quedan: ", tracked_count, ")");
         return sig_id;
      }
   }
   return "";
}

int CountActiveBotTrades()
{
   return tracked_count;
}

//================ BOT STATUS CHECK =================//
bool IsBotRunning()
{
   datetime current_time = TimeCurrent();
   if(current_time - last_bot_status_check < 5)
      return true;

   last_bot_status_check = current_time;

   int handle = FileOpen(Bot_Status_File, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("BOT STATUS NO DETECTADO");
      return false;
   }

   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);
   FileClose(handle);

   if(StringFind(content, "\"running\": true") < 0)
   {
      Print("BOT EN STOP (running=false)");
      return false;
   }

   // Leer min_confidence sincronizado
   string mc_val = GetJSONValue(content, "min_confidence");
   if(mc_val != "")
   {
      double mc = StringToDouble(mc_val);
      if(mc > 0.0 && mc <= 1.0)
         synced_min_confidence = mc;
   }

   // Leer max_concurrent_trades
   string mct_val = GetJSONValue(content, "max_concurrent_trades");
   if(mct_val != "")
   {
      int mct = (int)StringToInteger(mct_val);
      if(mct >= 1 && mct <= MAX_TRACKED_TRADES)
         synced_max_concurrent = mct;
   }

   // Leer lot_size
   string lot_val = GetJSONValue(content, "lot_size");
   if(lot_val != "")
   {
      double lot = StringToDouble(lot_val);
      if(lot >= 0.01 && lot <= 10.0)
         synced_lot_size = lot;
   }

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
      if(c == ',' || c == '}' || c == '\"' || c == '\n' || c == '\r')
         break;

      value += CharToString(c);
      pos++;
   }

   // Trim spaces
   StringTrimLeft(value);
   StringTrimRight(value);

   return value;
}

//================ READ SIGNAL =================//
bool ReadSignal(Signal &sig)
{
   int handle = FileOpen(Signal_File, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return false;

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

   // Leer lot_size de la senal si existe, sino usar el sincronizado
   string lot_str = GetJSONValue(content, "lot_size");
   if(lot_str != "")
      sig.lot_size = StringToDouble(lot_str);
   else
      sig.lot_size = synced_lot_size;

   // Verificar senal STOP
   if(StringFind(sig.signal_id, "_STOP") >= 0)
   {
      Print("SENAL STOP RECIBIDA");
      sig.action = "NONE";
      // Borrar signal.json
      FileDelete(Signal_File);
      return false;
   }

   // Verificar senal NONE
   if(StringFind(sig.signal_id, "_NONE") >= 0)
   {
      FileDelete(Signal_File);
      return false;
   }

   // Verificar si ya procesada
   if(sig.signal_id == "" || sig.signal_id == last_signal_id)
      return false;

   // Verificar confidence
   if(sig.confidence < synced_min_confidence)
   {
      Print("Confianza baja: ", sig.confidence, " < ", DoubleToString(synced_min_confidence, 2));
      // Borrar signal.json para que Python pueda enviar nueva
      FileDelete(Signal_File);
      last_signal_id = sig.signal_id;
      return false;
   }

   Print("SENAL VALIDA DETECTADA");
   Print("   ID: ", sig.signal_id);
   Print("   Action: ", sig.action);
   Print("   Confidence: ", DoubleToString(sig.confidence, 2));
   Print("   Lot: ", DoubleToString(sig.lot_size, 2));

   last_signal_id = sig.signal_id;

   return true;
}

//================ DELETE SIGNAL FILE =================//
void DeleteSignalFile()
{
   if(FileIsExist(Signal_File))
   {
      FileDelete(Signal_File);
      Print("signal.json consumido y eliminado");
   }
}

//================ WRITE FEEDBACK (INDIVIDUAL FILE) =================//
void WriteTradeFeedbackQueued(string signal_id, string result, double pips)
{
   // Crear carpeta si no existe
   FolderCreate(Feedback_Folder);

   // Nombre unico basado en signal_id y timestamp
   string safe_id = signal_id;
   StringReplace(safe_id, ":", "_");
   StringReplace(safe_id, " ", "_");

   string filename = Feedback_Folder + "fb_" + safe_id + ".json";

   int handle = FileOpen(filename, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("ERROR: No se pudo escribir feedback en ", filename);
      // Intentar con nombre simplificado
      filename = Feedback_Folder + "fb_" + IntegerToString(GetTickCount()) + ".json";
      handle = FileOpen(filename, FILE_WRITE | FILE_TXT | FILE_ANSI);
      if(handle == INVALID_HANDLE)
      {
         Print("ERROR CRITICO: No se pudo escribir feedback");
         return;
      }
   }

   string json =
      "{\n"
      "  \"signal_id\": \"" + signal_id + "\",\n"
      "  \"result\": \"" + result + "\",\n"
      "  \"pips\": " + DoubleToString(pips, 2) + ",\n"
      "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"\n"
      "}";

   FileWriteString(handle, json);
   FileClose(handle);

   Print("FEEDBACK ESCRITO: ", result, " | Pips: ", DoubleToString(pips, 2), " | Archivo: ", filename);
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

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   ulong position_id = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);

   // === TRADE ABIERTO ===
   if(entry == DEAL_ENTRY_IN)
   {
      if(pending_signal_id != "")
      {
         AddTradeMapping(position_id, pending_signal_id);
         Print("TRADE ABIERTO: Posicion ", position_id, " mapeada a ", pending_signal_id);
         pending_signal_id = "";
      }
      return;
   }

   // === TRADE CERRADO ===
   if(entry == DEAL_ENTRY_OUT)
   {
      double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
      double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
      double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
      double total_profit = profit + swap + commission;
      double pips = profit / 10.0;

      string res = total_profit >= 0 ? "WIN" : "LOSS";

      // Buscar signal_id por position_id
      string sig_id = FindAndRemoveSignalId(position_id);

      if(sig_id != "")
      {
         // Trade del bot - escribir feedback individual
         WriteTradeFeedbackQueued(sig_id, res, pips);
         Print("TRADE BOT CERRADO: ", res, " | ", DoubleToString(pips, 2), " pips | Signal: ", sig_id);
      }
      else
      {
         Print("Trade manual/externo cerrado: ", res, " | ", DoubleToString(pips, 2), " pips (sin feedback)");
      }
   }
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

   // MACD histogram
   double macd_histogram = macd_main[0] - macd_signal[0];

   // JSON
   string json = "{\n";
   json += "  \"symbol\": \"" + _Symbol + "\",\n";
   json += "  \"timeframe\": \"" + EnumToString(Period()) + "\",\n";
   json += "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",\n";
   json += "  \"bid\": " + DoubleToString(bid, _Digits) + ",\n";
   json += "  \"ask\": " + DoubleToString(ask, _Digits) + ",\n";
   json += "  \"indicators\": {\n";
   json += "    \"rsi\": " + DoubleToString(rsi_buffer[0], 2) + ",\n";
   json += "    \"macd\": {\n";
   json += "      \"main\": " + DoubleToString(macd_main[0], _Digits) + ",\n";
   json += "      \"signal\": " + DoubleToString(macd_signal[0], _Digits) + ",\n";
   json += "      \"histogram\": " + DoubleToString(macd_histogram, _Digits) + "\n";
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
      Print("Error inicializando indicadores");
      return false;
   }

   Print("Indicadores OK");
   return true;
}

//================ ON TICK =================//
void OnTick()
{
   // Escribir market data periodicamente
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
         Print("EA EN ESPERA - Bot Python detenido");
         logged = true;
      }
      return;
   }
   static bool logged = false;
   logged = false;

   // Verificar limite de trades concurrentes del bot
   int active_bot_trades = CountActiveBotTrades();
   if(active_bot_trades >= synced_max_concurrent)
      return;

   // Leer senal
   Signal sig;
   if(!ReadSignal(sig))
      return;

   if(sig.action == "NONE")
   {
      DeleteSignalFile();
      return;
   }

   // Calcular pip value
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits == 5 || digits == 3)
      pip_value = 10 * _Point;
   else
      pip_value = _Point;

   stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);

   double lot = sig.lot_size;
   double entry_price, sl_price, tp_price;

   // Guardar pending_signal_id ANTES de abrir trade
   // Se mapeara en OnTradeTransaction cuando DEAL_ENTRY_IN llegue
   pending_signal_id = sig.signal_id;

   bool order_ok = false;

   if(sig.action == "BUY")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl_price = entry_price - (sig.sl_pips * pip_value);
      tp_price = entry_price + (sig.tp_pips * pip_value);

      double min_distance = stops_level * _Point;
      if(stops_level > 0)
      {
         if((entry_price - sl_price) < min_distance)
            sl_price = entry_price - min_distance;
         if((tp_price - entry_price) < min_distance)
            tp_price = entry_price + min_distance;
      }

      Print("BUY @ ", DoubleToString(entry_price, _Digits),
            " | SL: ", DoubleToString(sl_price, _Digits),
            " | TP: ", DoubleToString(tp_price, _Digits),
            " | Lot: ", DoubleToString(lot, 2));

      order_ok = trade.Buy(lot, _Symbol, entry_price, sl_price, tp_price);
   }
   else if(sig.action == "SELL")
   {
      entry_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl_price = entry_price + (sig.sl_pips * pip_value);
      tp_price = entry_price - (sig.tp_pips * pip_value);

      double min_distance = stops_level * _Point;
      if(stops_level > 0)
      {
         if((sl_price - entry_price) < min_distance)
            sl_price = entry_price + min_distance;
         if((entry_price - tp_price) < min_distance)
            tp_price = entry_price - min_distance;
      }

      Print("SELL @ ", DoubleToString(entry_price, _Digits),
            " | SL: ", DoubleToString(sl_price, _Digits),
            " | TP: ", DoubleToString(tp_price, _Digits),
            " | Lot: ", DoubleToString(lot, 2));

      order_ok = trade.Sell(lot, _Symbol, entry_price, sl_price, tp_price);
   }

   if(order_ok)
   {
      Print("ORDEN ", sig.action, " ABIERTA (Signal: ", sig.signal_id, ")");
      // El mapeo position_id -> signal_id se hace en OnTradeTransaction DEAL_ENTRY_IN
   }
   else
   {
      Print("ERROR ABRIENDO ORDEN: ", trade.ResultRetcodeDescription());
      pending_signal_id = "";  // Limpiar pending si fallo
   }

   // SIEMPRE borrar signal.json despues de procesarlo
   // Esto evita que se re-lea la misma senal
   DeleteSignalFile();
}

//================ INIT =================//
int OnInit()
{
   Print("========================================");
   Print("EA SignalExecutor v6.0 - MULTI-TRADE");
   Print("Soporte multi-trade + feedback queue");
   Print("========================================");

   if(!InitIndicators())
   {
      Print("Fallo al inicializar");
      return INIT_FAILED;
   }

   // Crear carpeta de feedback
   FolderCreate(Feedback_Folder);

   // Inicializar tracking
   tracked_count = 0;
   pending_signal_id = "";

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

   Print("EA SignalExecutor v6.0 DETENIDO (trades trackeados: ", tracked_count, ")");
}
