import pandas as pd
import numpy as np
from talib import ADX, RSI, BBANDS, SAR
import threading
import tkinter as tk
from tkinter import ttk
from ibapi.client import EClient
from ibapi.contract import Contract
from dexscreener import DexScreener
from dtw import dtw
import webbrowser
from tradingview_ta import TA_Handler, Interval
from tradingview_widget import TradingViewWidget

# Set up Interactive Brokers API
class IBClient(EClient):
    def __init__(self):
        EClient.__init__(self, self)

ib_client = IBClient()
ib_client.connect("127.0.0.1", 7497, clientId=1)

# Set up Dexscreener API
dex_client = DexScreener()

# Function to calculate the distance between two trends using DTW
def dtw_distance(trend1, trend2):
    return dtw(trend1['Close'], trend2['Close']).distance

# Function to find the top 3 most similar trends
def get_top_trends(data, n=3):
    distances = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            distances.append((data.iloc[i], dtw_distance(data.iloc[i], data.iloc[j])))
    return data.iloc[sorted(distances, key=lambda x: x[1])[:n]]

# Define the trend following algorithm
def trend_following(data, window_short=50, window_long=200, adx_period=14, rsi_period=14, bollinger_period=20, sar_acceleration=0.02, sar_maximum=0.2, volatility=0.1):
    # Adaptive timeframe adjustment
    window_short = max(20, int(window_short * (1 + volatility)))
    window_long = max(20, int(window_long * (1 + volatility)))

    # Calculate moving averages
    ma_short = data['Close'].rolling(window=window_short).mean()
    ma_long = data['Close'].rolling(window=window_long).mean()
    
    # Calculate ADX
    adx = ADX(data['High'], data['Low'], data['Close'], timeperiod=adx_period)
    
    # Calculate RSI
    rsi = RSI(data['Close'], timeperiod=rsi_period)
    
    # Calculate Bollinger Bands
    upper_band, middle_band, lower_band = BBANDS(data['Close'], timeperiod=bollinger_period, nbdevup=2, nbdevdn=2, matype=0)
    
    # Calculate Parabolic SAR
    sar = SAR(data['High'], data['Low'], acceleration=sar_acceleration, maximum=sar_maximum)
    
    # Combine signals into a DataFrame
    signals = pd.DataFrame({
        'MA Short': ma_short,
        'MA Long': ma_long,
        'ADX': adx,
        'RSI': rsi,
        'Upper Bollinger': upper_band,
        'Lower Bollinger': lower_band,
        'Parabolic SAR': sar
    })
    
    # Define the trend-following logic
    signals['Trend'] = np.where(
        (signals['MA Short'] > signals['MA Long']) & 
        (signals['ADX'] > 25) & 
        (signals['RSI'] > 50) & 
        (data['Close'] > signals['Parabolic SAR']),
        'Uptrend',
        np.where(
            (signals['MA Short'] < signals['MA Long']) & 
            (signals['ADX'] > 25) & 
            (signals['RSI'] < 50) & 
            (data['Close'] < signals['Parabolic SAR']),
            'Downtrend',
            'No Trend'
        )
    )
    
    return signals

# Get live data from Dexscreener
def get_dex_data(symbol):
    data = dex_client.get_symbol_data(symbol)
    return pd.DataFrame(data)

def fetch_data(symbol):
    try:
        historical_data = get_ib_data(symbol)
        live_data = get_dex_data(symbol)
        data = pd.concat([historical_data, live_data])
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# Define the asset classes and their corresponding assets
asset_classes = {
    "Technology": ["AAPL", "GOOG", "MSFT", "CSCO", "INTC", "NVDA"],
    "Finance": ["JPM", "V", "MA", "WMT"],
    "Healthcare": ["JNJ", "MRK", "ABBV", "PFE"],
    "Consumer Goods": ["KO", "MCD", "T"],
    "Industrials": ["BRK-A"], 
    "Bitcoin Forks": ["BTC", "BCH", "BSV"],
    "Ethereum Tokens": ["ETH", "ERC-20 tokens"],
    "DeFi Tokens": ["UNI", "LINK", "AAVE"],
    "Stablecoins": ["USDT", "USDC", "DAI"],
    "Altcoins": ["LTC", "XRP", "XLM"],
}

# Define the functions for FVG and Orderblock detection
def check_disp(o, c, long_atr, disp_x):
    return np.abs(o - c) > long_atr * disp_x

def update_price(df, o_arr, h_arr, l_arr, c_arr, max_arr_size):
    if len(o_arr) == 0 or df['open'].iloc[-1] != df['open'].iloc[-2]:
        o_arr.insert(0, df['open'].iloc[-2])
        h_arr.insert(0, df['high'].iloc[-2])
        l_arr.insert(0, df['low'].iloc[-2])
        c_arr.insert(0, df['close'].iloc[-2])
    if len(o_arr) > max_arr_size:
        o_arr.pop()
        h_arr.pop()
        l_arr.pop()
        c_arr.pop()

def check_fvg(df, o_arr, h_arr, l_arr, c_arr, fvg_bull, fvg_bear, long_atr, disp_x, color):
    # Multi-timeframe Fair Value Gaps
    for i in range(len(fvg_bull)):
        fvg_bull[i] = check_fvg_mtf(df, o_arr[i], h_arr[i], l_arr[i], fvg_bull[i], long_atr, disp_x, color)
    for i in range(len(fvg_bear)):
        fvg_bear[i] = check_fvg_mtf(df, o_arr[i], h_arr[i], l_arr[i], fvg_bear[i], long_atr, disp_x, color)

def check_fvg_mtf(df, o, h, l, fvg, long_atr, disp_x, color):
    # Highest Price of the last 20, 40, 60 days
    highs = df['High'].rolling(20).max().fillna(0)
    highs = highs.rolling(40).max().fillna(0)
highs = highs.rolling(60).max().fillna(0)

# Lowest Price of the last 20, 40, 60 days
lows = df['Low'].rolling(20).min().fillna(0)
lows = lows.rolling(40).min().fillna(0)
lows = lows.rolling(60).min().fillna(0)

# Midpoint Price of the last 20, 40, 60 days
midpoints = (df['High'] + df['Low']).rolling(20).mean().fillna(0)
midpoints = midpoints.rolling(40).mean().fillna(0)
midpoints = midpoints.rolling(60).mean().fillna(0)

# Check for FVGs
for i in range(len(highs)):
    if o > highs[i] and h > highs[i]:
        fvg.append((h, l, color))

def check_orderblock(df, o, h, l, color, timeframe):
# Calculate the number of days for each timeframe
days_20 = 20 * timeframe
days_40 = 40 * timeframe
days_60 = 60 * timeframe

# Calculate the highest and lowest prices of the specified number of days
high_20 = df['High'].rolling(days_20).max().fillna(0)
low_20 = df['Low'].rolling(days_20).min().fillna(0)
high_40 = df['High'].rolling(days_40).max().fillna(0)
low_40 = df['Low'].rolling(days_40).min().fillna(0)
high_60 = df['High'].rolling(days_60).max().fillna(0)
low_60 = df['Low'].rolling(days_60).min().fillna(0)

# Calculate the midpoint price of the specified number of days
mid_20 = (high_20 + low_20) / 2
mid_40 = (high_40 + low_40) / 2
mid_60 = (high_60 + low_60) / 2

# Check for order blocks at high, low, and midpoint
orderblock_high_20 = (o > h) and (h > high_20)
orderblock_low_20 = (o < l) and (l < low_20)
orderblock_mid_20 = (o > h) and (h > mid_20)

orderblock_high_40 = (o > h) and (h > high_40)
orderblock_low_40 = (o < l) and (l < low_40)
orderblock_mid_40 = (o > h) and (h > mid_40)

orderblock_high_60 = (o > h) and (h > high_60)
orderblock_low_60 = (o < l) and (l < low_60)
orderblock_mid_60 = (o > h) and (h > mid_60)

return orderblock_high_20, orderblock_low_20, orderblock_mid_20, orderblock_high_40, orderblock_low_40, orderblock_mid_40, orderblock_high_60, orderblock_low_60, orderblock_mid_60

def overlap(top1, bot1, top2, bot2):
return (np.abs(top1 - bot1) + np.abs(top2 - bot2)) > (max(top1, top2) - min(bot1, bot2))

root = tk.Tk()
root.title(“Trend Following Algorithm”)
frame = ttk.Frame(root, padding=“10”)
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

symbol_label = ttk.Label(frame, text=“Symbol:”)
symbol_label.grid(row=0, column=0, sticky=tk.W)
symbol_entry = ttk.Entry(frame)
symbol_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

asset_class_combobox = ttk.Combobox(frame, values=list(asset_classes.keys()))
asset_class_combobox.set(””)  # Set the default value to an empty string
asset_class_combobox.grid(row=0, column=2, sticky=tk.W)

asset_combobox = ttk.Combobox(frame)
asset_combobox.grid(row=0, column=3, sticky=tk.W)

button = ttk.Button(frame, text=“Show Trends”)
button.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E))

def update_assets(event=None):
asset_class = asset_class_combobox.get()
if asset_class:
assets = asset_classes[asset_class]
asset_combobox[‘values’] = assets
asset_combobox.set(””)  # Reset the selected asset

asset_class_combobox.bind(”<>”, update_assets)

def on_show_trends():
symbol = asset_combobox.get()
data = fetch_data(symbol)
if data is not None:
signals = trend_following(data)
text_box = tk.Text(root)
text_box.insert(‘1.0’, str(signals))
text_box.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E))

    # Calculate the top 3 most similar trends
    top_trends = get_top_trends(data)

    # Plot the top 3 trends on the chart using the TA_Handler class
    ta_handler = TA_Handler(data['Close'])
    for trend in top_trends:
        ta_handler.plot(trend['Close'], color='red', linewidth=2)
else:
    error_label = tk.Label(root, text="Error: Unable to fetch data")
    error_label.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E))

button.config(command=on_show_trends)

root.mainloop()