from datetime import datetime, timedelta

def get(client, symbol, period_time, ichimoku_tenkan_sen_period, ichimoku_kijun_sen_period, 
    ichimoku_senkou_span_b_period, ichimoku_senkou_span_lag_period, ichimoku_chikou_span_period) -> list:

    period_time_to_period_time_minutes = {
        "1m": 1,
        "5m": 5,
        "1h": 60,
        "1d": 1440
    }

    current_time = datetime.fromtimestamp(client.fetch_ticker(symbol)["timestamp"] / 1000)
    back_time = timedelta(minutes=(period_time_to_period_time_minutes[period_time] + 1) * max(ichimoku_tenkan_sen_period, ichimoku_kijun_sen_period, 
                            ichimoku_senkou_span_b_period, ichimoku_chikou_span_period))

    all_previous_prices = client.fetch_ohlcv(symbol, period_time, since=((current_time - back_time).timestamp()) * 1000)

    previous_close_prices = [price[4] for price in all_previous_prices]
    previous_high_prices = [price[2] for price in all_previous_prices]

    #Calculate Tenkan Sen
    tenkan_sen = (max(previous_high_prices[-ichimoku_tenkan_sen_period:]) + min(previous_high_prices[-ichimoku_tenkan_sen_period:])) / 2

    #Calculate Kijun Sen
    kijun_sen = (max(previous_high_prices[-ichimoku_kijun_sen_period:]) + min(previous_high_prices[-ichimoku_kijun_sen_period:])) / 2

    #Calculate Senkou Span A
    old_tenkan_sen = (max(previous_high_prices[-(ichimoku_tenkan_sen_period + ichimoku_senkou_span_lag_period):-ichimoku_senkou_span_lag_period]) + min(previous_high_prices[-(ichimoku_tenkan_sen_period + ichimoku_senkou_span_lag_period):-ichimoku_senkou_span_lag_period])) / 2
    old_kijun_sen = (max(previous_high_prices[-(ichimoku_kijun_sen_period + ichimoku_senkou_span_lag_period):-ichimoku_senkou_span_lag_period]) + min(previous_high_prices[-(ichimoku_kijun_sen_period + ichimoku_senkou_span_lag_period):-ichimoku_senkou_span_lag_period])) / 2
    senkou_span_a = (old_tenkan_sen + old_kijun_sen) / 2
    
    #Calculate Senkou Span B
    senkou_span_b = (max(previous_high_prices[2 * -ichimoku_senkou_span_b_period:-ichimoku_senkou_span_b_period]) + min(previous_high_prices[2 * -ichimoku_senkou_span_b_period:-ichimoku_senkou_span_b_period])) / 2

    #Calculate Chikou Span
    chikou_span = client.fetch_ticker(symbol)["close"]

    #Get Chikou Span Occurence Price 
    old_price = previous_close_prices[-(ichimoku_chikou_span_period + 1)]

    #Get Current Price
    price = client.fetch_ticker(symbol)["close"]

    ichimoku_cloud_data = [tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span, old_price, price]

    return(ichimoku_cloud_data)

def signal(previous_ichimoku_cloud: list):
    data = previous_ichimoku_cloud
    signals = []
    
    #Tenkan Sen / Kijun Sen Cross
    if (data[len(data) - 1][0] > data[len(data) - 1][1] and data[len(data) -2][0] < data[len(data) - 2][1]):
        current_signal = []
        current_signal.append("Tenkan Sen / Kijun Sen Cross")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif (data[len(data) - 1][0] < data[len(data) - 1][1] and data[len(data) -2][0] > data[len(data) - 2][1]):
        current_signal = []
        current_signal.append("Tenkan Sen / Kijun Sen Cross")
        current_signal.append("bearish")
        signals.append(current_signal)

    #Kijun Sen Cross
    if (data[len(data) - 1][6] > data[len(data) - 1][1] and data[len(data) -2][5] < data[len(data) - 2][1]):
        current_signal = []
        current_signal.append("Kijun Sen Cross")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif (data[len(data) - 1][6] < data[len(data) - 1][1] and data[len(data) -2][5] > data[len(data) - 2][1]):
        current_signal = []
        current_signal.append("Kijun Sen Cross")
        current_signal.append("bearish")
        signals.append(current_signal)

    #Kumo Breakout
    if data[len(data) - 1][6] > max(data[len(data) - 2][2], data[len(data) - 2][3]) and min(data[len(data) - 2][2], data[len(data) - 2][3]) < data[len(data) - 2][5] < max(data[len(data) - 2][2], data[len(data) - 2][3]):
        current_signal = []
        current_signal.append("Kumo Breakout")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif data[len(data) - 1][6] < min(data[len(data) - 2][2], data[len(data) - 2][3]) and min(data[len(data) - 2][2], data[len(data) - 2][3]) < data[len(data) - 2][5] < max(data[len(data) - 2][2], data[len(data) - 2][3]):
        current_signal = []
        current_signal.append("Kumo Breakout")
        current_signal.append("bearish")
        signals.append(current_signal)

    #Senkou Span Cross
    if data[len(data) - 1][2] > data[len(data) - 1][3] and data[len(data) - 2][2] < data[len(data) - 1][3]:
        current_signal = []
        current_signal.append("Senkou Span Cross")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif data[len(data) - 1][2] < data[len(data) - 1][3] and data[len(data) - 2][2] > data[len(data) - 1][3]:
        current_signal = []
        current_signal.append("Senkou Span Cross")
        current_signal.append("bearish")
        signals.append(current_signal)

    #Chikou Span Cross
    if data[len(data) - 1][4] > data[len(data) - 1][5] and data[len(data) - 1][4] < data[len(data) - 1][5]:
        current_signal = []
        current_signal.append("Chikou Span Cross")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif data[len(data) - 1][4] > data[len(data) - 1][5] and data[len(data) - 1][4] < data[len(data) - 1][5]:
        current_signal = []
        current_signal.append("Chikou Span Cross")
        current_signal.append("bearish")
        signals.append(current_signal)

    #Bull / Bear Check
    if data[len(data) - 1][2] > data[len(data) - 1][3]:
        current_signal = []
        current_signal.append("Bull Cloud")
        current_signal.append("bullish")
        signals.append(current_signal)
    elif data[len(data) - 1][2] < data[len(data) - 1][3]:
        current_signal = []
        current_signal.append("Bear Cloud")
        current_signal.append("bearish")
        signals.append(current_signal)

    return signals
