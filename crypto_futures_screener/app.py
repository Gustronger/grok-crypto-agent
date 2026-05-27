#!/usr/bin/env python3
"""
Crypto Futures Screener - Alat Screening Posisi Long/Short
Dibuat oleh GQCoding08 / GQ80 / G
Versi 1.0 - 27 Mei 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ccxt
import requests
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# ==================== KONFIGURASI ====================
st.set_page_config(
    page_title="GROK CRYPTO AGENT v1.5 | Smart Money Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Optimized for Mobile + Desktop
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem; 
        color: #00ff9d; 
        text-align: center; 
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem; 
        color: #00b8ff; 
        text-align: center;
        margin-bottom: 1rem;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main-header { font-size: 1.7rem; }
        .sub-header { font-size: 0.95rem; }
        .stMetric { font-size: 0.9rem; }
        .stButton>button { 
            font-size: 0.95rem; 
            padding: 0.5rem 1rem;
        }
        .stDataFrame { font-size: 0.85rem; }
    }
    
    .metric-positive {color: #00ff9d; font-weight: bold;}
    .metric-negative {color: #ff4b4b; font-weight: bold;}
    .stButton>button {
        background-color: #00ff9d; 
        color: black; 
        font-weight: bold;
        border-radius: 8px;
    }
    .analysis-box {
        background-color: #1a1a2e; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #00ff9d;
    }
    
    /* Better spacing on mobile */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FUNGSI ANALISA TEKNIKAL ====================

def calculate_swing_points(df, window=5):
    """Deteksi swing high dan swing low"""
    df = df.copy()
    df['swing_high'] = np.nan
    df['swing_low'] = np.nan
    
    for i in range(window, len(df) - window):
        # Swing High
        if all(df['high'].iloc[i] > df['high'].iloc[i-window:i]) and \
           all(df['high'].iloc[i] > df['high'].iloc[i+1:i+window+1]):
            df.loc[df.index[i], 'swing_high'] = df['high'].iloc[i]
        
        # Swing Low
        if all(df['low'].iloc[i] < df['low'].iloc[i-window:i]) and \
           all(df['low'].iloc[i] < df['low'].iloc[i+1:i+window+1]):
            df.loc[df.index[i], 'swing_low'] = df['low'].iloc[i]
    
    return df

def detect_market_structure(df):
    """Deteksi Market Structure: HH, HL, LH, LL, BOS, CHOCH"""
    df = df.copy()
    swings = calculate_swing_points(df)
    
    swing_highs = swings[swings['swing_high'].notna()][['timestamp', 'swing_high']].reset_index(drop=True)
    swing_lows = swings[swings['swing_low'].notna()][['timestamp', 'swing_low']].reset_index(drop=True)
    
    structure = []
    bias = "Neutral"
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        last_sh = swing_highs['swing_high'].iloc[-1]
        prev_sh = swing_highs['swing_high'].iloc[-2]
        last_sl = swing_lows['swing_low'].iloc[-1]
        prev_sl = swing_lows['swing_low'].iloc[-2]
        
        if last_sh > prev_sh and last_sl > prev_sl:
            bias = "Bullish (HH + HL)"
            structure.append("Higher Highs & Higher Lows → Potensi Long")
        elif last_sh < prev_sh and last_sl < prev_sl:
            bias = "Bearish (LH + LL)"
            structure.append("Lower Highs & Lower Lows → Potensi Short")
        elif last_sh > prev_sh and last_sl < prev_sl:
            bias = "Indecisive / Expanding Range"
            structure.append("Higher High + Lower Low → Breakout imminent")
        else:
            bias = "Consolidation / Reversal possible"
            structure.append("Mixed structure - tunggu konfirmasi BOS")
    
    return bias, structure, swing_highs, swing_lows

def calculate_fibonacci_levels(high, low, direction="bullish"):
    """Hitung level Fibonacci Retracement & Extension"""
    diff = high - low
    
    if direction == "bullish":
        levels = {
            'Fib 0.236': round(high - 0.236 * diff, 6),
            'Fib 0.382': round(high - 0.382 * diff, 6),
            'Fib 0.5': round(high - 0.5 * diff, 6),
            'Fib 0.618': round(high - 0.618 * diff, 6),
            'Fib 0.786': round(high - 0.786 * diff, 6),
            'Fib 1.0 (Swing Low)': round(low, 6),
            'TP1 (1.272 Ext)': round(low + 1.272 * diff, 6),
            'TP2 (1.618 Ext)': round(low + 1.618 * diff, 6),
            'TP3 (2.0 Ext)': round(low + 2.0 * diff, 6),
        }
    else:  # bearish
        levels = {
            'Fib 0.236': round(low + 0.236 * diff, 6),
            'Fib 0.382': round(low + 0.382 * diff, 6),
            'Fib 0.5': round(low + 0.5 * diff, 6),
            'Fib 0.618': round(low + 0.618 * diff, 6),
            'Fib 0.786': round(low + 0.786 * diff, 6),
            'Fib 1.0 (Swing High)': round(high, 6),
            'TP1 (1.272 Ext)': round(high - 1.272 * diff, 6),
            'TP2 (1.618 Ext)': round(high - 1.618 * diff, 6),
            'TP3 (2.0 Ext)': round(high - 2.0 * diff, 6),
        }
    return levels

def find_order_blocks(df, lookback=20):
    """Cari Order Block sederhana (Smart Money Concept dasar)"""
    df = df.copy()
    order_blocks = []
    
    for i in range(lookback, len(df)):
        # Bullish Order Block: last bearish candle sebelum strong bullish move
        if (df['close'].iloc[i] > df['open'].iloc[i] and  # bullish candle
            df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # previous bearish
            (df['close'].iloc[i] - df['open'].iloc[i]) > (df['high'].iloc[i-1] - df['low'].iloc[i-1]) * 1.5):
            
            ob_low = df['low'].iloc[i-1]
            ob_high = df['high'].iloc[i-1]
            order_blocks.append({
                'type': 'Demand (Bullish OB)',
                'index': i-1,
                'low': ob_low,
                'high': ob_high,
                'timestamp': df['timestamp'].iloc[i-1]
            })
        
        # Bearish Order Block
        if (df['close'].iloc[i] < df['open'].iloc[i] and
            df['close'].iloc[i-1] > df['open'].iloc[i-1] and
            (df['open'].iloc[i] - df['close'].iloc[i]) > (df['high'].iloc[i-1] - df['low'].iloc[i-1]) * 1.5):
            
            ob_low = df['low'].iloc[i-1]
            ob_high = df['high'].iloc[i-1]
            order_blocks.append({
                'type': 'Supply (Bearish OB)',
                'index': i-1,
                'low': ob_low,
                'high': ob_high,
                'timestamp': df['timestamp'].iloc[i-1]
            })
    
    return order_blocks[-3:] if order_blocks else []  # ambil 3 terakhir


def detect_fvg(df, min_gap_pct=0.25):
    """Detect Fair Value Gap (FVG) - Smart Money Concept lanjutan
    Bullish FVG: Gap antara high candle-2 dan low candle saat ini setelah strong bullish move
    Bearish FVG: Gap antara low candle-2 dan high candle saat ini setelah strong bearish move
    """
    fvgs = []
    for i in range(2, len(df)):
        candle1 = df.iloc[i-2]
        candle2 = df.iloc[i-1]
        candle3 = df.iloc[i]
        
        # Bullish FVG (inefficiency di atas candle-2 high)
        if candle1['high'] < candle3['low']:
            gap_size = candle3['low'] - candle1['high']
            gap_pct = (gap_size / candle2['close']) * 100
            if gap_pct >= min_gap_pct:
                fvgs.append({
                    'type': 'Bullish FVG (Demand)',
                    'index': i-1,
                    'bottom': candle1['high'],
                    'top': candle3['low'],
                    'timestamp': candle2['timestamp'],
                    'gap_pct': round(gap_pct, 2)
                })
        
        # Bearish FVG (inefficiency di bawah candle-2 low)
        if candle1['low'] > candle3['high']:
            gap_size = candle1['low'] - candle3['high']
            gap_pct = (gap_size / candle2['close']) * 100
            if gap_pct >= min_gap_pct:
                fvgs.append({
                    'type': 'Bearish FVG (Supply)',
                    'index': i-1,
                    'bottom': candle3['high'],
                    'top': candle1['low'],
                    'timestamp': candle2['timestamp'],
                    'gap_pct': round(gap_pct, 2)
                })
    
    # Return only recent FVGs (max 6)
    return fvgs[-6:] if fvgs else []

def calculate_atr(df, period=14):
    """Average True Range"""
    df = df.copy()
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(period).mean()
    return df['atr'].iloc[-1] if not pd.isna(df['atr'].iloc[-1]) else (df['high'].iloc[-1] - df['low'].iloc[-1])

def generate_trading_setup(df, current_price, bias, fib_levels, order_blocks, atr):
    """Generate rekomendasi entry, SL, TP berdasarkan semua analisa"""
    setup = {
        'direction': 'NEUTRAL',
        'entry_zone_low': None,
        'entry_zone_high': None,
        'stop_loss': None,
        'tp1': None,
        'tp2': None,
        'tp3': None,
        'risk_reward': None,
        'confidence': 0,
        'reason': []
    }
    
    if 'Bullish' in bias:
        setup['direction'] = 'LONG'
        # Entry di dekat Fib 0.618 atau Demand OB
        entry_candidates = [fib_levels.get('Fib 0.618', current_price * 0.99)]
        if order_blocks:
            for ob in order_blocks:
                if ob['type'] == 'Demand (Bullish OB)':
                    entry_candidates.append((ob['low'] + ob['high']) / 2)
        
        setup['entry_zone_low'] = round(min(entry_candidates) * 0.995, 6)
        setup['entry_zone_high'] = round(max(entry_candidates) * 1.005, 6)
        
        # SL di bawah demand zone atau recent swing low - ATR buffer
        sl_base = min([ob['low'] for ob in order_blocks if ob['type'] == 'Demand (Bullish OB)'] or [current_price * 0.97])
        setup['stop_loss'] = round(sl_base - (atr * 0.8), 6)
        
        # TP berdasarkan Fib Extension
        setup['tp1'] = fib_levels.get('TP1 (1.272 Ext)', current_price * 1.03)
        setup['tp2'] = fib_levels.get('TP2 (1.618 Ext)', current_price * 1.05)
        setup['tp3'] = fib_levels.get('TP3 (2.0 Ext)', current_price * 1.08)
        
        setup['reason'].append("Bullish structure + Fib retracement + Demand zone confluence")
        
    elif 'Bearish' in bias:
        setup['direction'] = 'SHORT'
        entry_candidates = [fib_levels.get('Fib 0.618', current_price * 1.01)]
        if order_blocks:
            for ob in order_blocks:
                if ob['type'] == 'Supply (Bearish OB)':
                    entry_candidates.append((ob['low'] + ob['high']) / 2)
        
        setup['entry_zone_low'] = round(min(entry_candidates) * 0.995, 6)
        setup['entry_zone_high'] = round(max(entry_candidates) * 1.005, 6)
        
        sl_base = max([ob['high'] for ob in order_blocks if ob['type'] == 'Supply (Bearish OB)'] or [current_price * 1.03])
        setup['stop_loss'] = round(sl_base + (atr * 0.8), 6)
        
        setup['tp1'] = fib_levels.get('TP1 (1.272 Ext)', current_price * 0.97)
        setup['tp2'] = fib_levels.get('TP2 (1.618 Ext)', current_price * 0.95)
        setup['tp3'] = fib_levels.get('TP3 (2.0 Ext)', current_price * 0.92)
        
        setup['reason'].append("Bearish structure + Fib retracement + Supply zone confluence")
    
    # Hitung Risk Reward (pakai TP2)
    if setup['stop_loss'] and setup['entry_zone_low'] and setup['tp2']:
        risk = abs(setup['entry_zone_low'] - setup['stop_loss'])
        reward = abs(setup['tp2'] - setup['entry_zone_low'])
        if risk > 0:
            setup['risk_reward'] = round(reward / risk, 2)
    
    # Confidence score sederhana
    conf = 50
    if 'Bullish' in bias or 'Bearish' in bias:
        conf += 20
    if order_blocks:
        conf += 15
    if setup['risk_reward'] and setup['risk_reward'] > 2:
        conf += 15
    setup['confidence'] = min(conf, 95)
    
    return setup

# ==================== DATA FETCHER ====================

@st.cache_data(ttl=300)
def get_top_futures_coins(limit=50):
    """Ambil daftar koin populer yang biasanya punya futures (fallback friendly)"""
    try:
        # Prioritaskan CoinGecko (lebih reliable di banyak lokasi)
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'volume_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': False
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        # Daftar koin yang biasanya punya futures perpetual
        common_futures_coins = {
            'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'SHIB', 'DOT', 'LINK',
            'TON', 'TRX', 'NEAR', 'MATIC', 'LTC', 'BCH', 'UNI', 'ATOM', 'XLM', 'ETC',
            'FIL', 'APT', 'ARB', 'OP', 'SUI', 'PEPE', 'WIF', 'BONK', 'FLOKI', 'JUP'
        }
        
        coins_data = []
        for coin in data:
            symbol = coin['symbol'].upper()
            if symbol in common_futures_coins and coin.get('total_volume', 0) > 3_000_000:
                coins_data.append({
                    'symbol': symbol,
                    'name': coin['name'],
                    'price': coin['current_price'],
                    'market_cap': coin.get('market_cap', 0),
                    'volume_24h': coin.get('total_volume', 0),
                    'change_24h': coin.get('price_change_percentage_24h', 0),
                    'futures_symbol': f"{symbol}/USDT:USDT"
                })
        
        if coins_data:
            df = pd.DataFrame(coins_data)
            df = df.sort_values('volume_24h', ascending=False).head(limit)
            return df.reset_index(drop=True)
        else:
            raise Exception("No coins found from CoinGecko")
            
    except Exception as e:
        # Fallback jika CoinGecko juga bermasalah
        st.warning(f"⚠️ Gagal mengambil data real-time. Menampilkan data contoh. Error: {str(e)[:100]}")
        return pd.DataFrame([
            {'symbol': 'BTC', 'name': 'Bitcoin', 'price': 68000, 'volume_24h': 25000000000, 'change_24h': 1.2, 'futures_symbol': 'BTC/USDT:USDT'},
            {'symbol': 'ETH', 'name': 'Ethereum', 'price': 3200, 'volume_24h': 12000000000, 'change_24h': -0.8, 'futures_symbol': 'ETH/USDT:USDT'},
            {'symbol': 'SOL', 'name': 'Solana', 'price': 145, 'volume_24h': 4500000000, 'change_24h': 3.5, 'futures_symbol': 'SOL/USDT:USDT'},
            {'symbol': 'XRP', 'name': 'Ripple', 'price': 0.52, 'volume_24h': 1800000000, 'change_24h': 2.1, 'futures_symbol': 'XRP/USDT:USDT'},
            {'symbol': 'DOGE', 'name': 'Dogecoin', 'price': 0.15, 'volume_24h': 950000000, 'change_24h': -1.5, 'futures_symbol': 'DOGE/USDT:USDT'},
        ])

@st.cache_data(ttl=120)
def fetch_ohlcv(symbol, timeframe='1h', limit=100):
    """Fetch OHLCV dari Binance Futures"""
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        return df
    except Exception as e:
        st.warning(f"Gagal fetch data {symbol} {timeframe}: {e}")
        return None

def get_news_sentiment(symbol):
    """Ambil link berita & sentiment sederhana"""
    links = {
        'CoinMarketCap': f"https://coinmarketcap.com/currencies/{symbol.lower()}/",
        'CoinGecko': f"https://www.coingecko.com/en/coins/{symbol.lower()}",
        'TradingView': f"https://www.tradingview.com/symbols/{symbol.upper()}USDT/",
        'Coinglass': f"https://www.coinglass.com/tv/{symbol.upper()}",
        'Investing': f"https://www.investing.com/crypto/{symbol.lower()}"
    }
    return links


def get_funding_and_oi(symbol):
    """Ambil Funding Rate & Open Interest dari Binance Futures (sangat penting untuk futures trading)"""
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Funding Rate
        funding = exchange.fetch_funding_rate(symbol)
        funding_rate = funding.get('fundingRate', 0) * 100  # dalam persen
        next_funding = funding.get('nextFundingTime')
        
        # Open Interest
        oi_data = exchange.fetch_open_interest(symbol)
        open_interest = oi_data.get('openInterestAmount', 0) if oi_data else 0
        
        return {
            'funding_rate': round(funding_rate, 4),
            'next_funding': next_funding,
            'open_interest': open_interest,
            'symbol': symbol
        }
    except Exception as e:
        return {
            'funding_rate': None,
            'next_funding': None,
            'open_interest': None,
            'error': str(e)
        }


# ==================== MULTI-TIMEFRAME & LIQUIDITY (AGENT LEVEL) ====================

def analyze_multi_timeframe(symbol, primary_tf='1h'):
    """Analisa Multi-Timeframe Confluence untuk agent crypto"""
    timeframes = ['15m', '30m', '1h', '4h', '1d']
    results = {}
    
    for tf in timeframes:
        try:
            df = fetch_ohlcv(symbol, timeframe=tf, limit=80)
            if df is not None and len(df) > 20:
                bias, _, _, _ = detect_market_structure(df)
                atr = calculate_atr(df)
                results[tf] = {
                    'bias': bias,
                    'atr': round(atr, 4),
                    'last_close': round(df['close'].iloc[-1], 4)
                }
            else:
                results[tf] = {'bias': 'Data kurang', 'atr': 0}
        except:
            results[tf] = {'bias': 'Error', 'atr': 0}
    
    # Hitung Confluence Score
    bullish_count = sum(1 for r in results.values() if 'Bullish' in r.get('bias', ''))
    bearish_count = sum(1 for r in results.values() if 'Bearish' in r.get('bias', ''))
    
    if bullish_count > bearish_count:
        overall = f"Bullish Confluence ({bullish_count}/5 TF)"
        score = int((bullish_count / 5) * 100)
    elif bearish_count > bullish_count:
        overall = f"Bearish Confluence ({bearish_count}/5 TF)"
        score = int((bearish_count / 5) * 100)
    else:
        overall = "Mixed / Sideways"
        score = 50
    
    return {
        'timeframes': results,
        'overall_bias': overall,
        'confluence_score': score,
        'primary_tf': primary_tf
    }


def detect_liquidity_sweep(df):
    """Deteksi Liquidity Sweep / Inducement (SMC Advanced)"""
    sweeps = []
    if len(df) < 30:
        return sweeps
    
    swings = calculate_swing_points(df)
    swing_highs = swings[swings['swing_high'].notna()]
    swing_lows = swings[swings['swing_low'].notna()]
    
    recent = df.tail(15)
    
    for i in range(len(recent) - 3):
        idx = recent.index[i]
        candle = recent.loc[idx]
        
        # Bullish sweep (break recent low then reverse up strongly)
        if not swing_lows.empty:
            recent_low = swing_lows['swing_low'].iloc[-1] if len(swing_lows) > 0 else df['low'].min()
            if candle['low'] < recent_low * 0.998 and candle['close'] > candle['open']:
                next_candles = df.loc[idx:idx+3] if idx+3 in df.index else recent.tail(3)
                if len(next_candles) >= 2 and next_candles['close'].iloc[-1] > next_candles['open'].iloc[-1]:
                    sweeps.append({
                        'type': 'Bullish Liquidity Sweep (Inducement)',
                        'level': round(recent_low, 4),
                        'timestamp': candle['timestamp'],
                        'description': 'Harga sweep low lalu balik naik kuat'
                    })
        
        # Bearish sweep (break recent high then reverse down)
        if not swing_highs.empty:
            recent_high = swing_highs['swing_high'].iloc[-1] if len(swing_highs) > 0 else df['high'].max()
            if candle['high'] > recent_high * 1.002 and candle['close'] < candle['open']:
                next_candles = df.loc[idx:idx+3] if idx+3 in df.index else recent.tail(3)
                if len(next_candles) >= 2 and next_candles['close'].iloc[-1] < next_candles['open'].iloc[-1]:
                    sweeps.append({
                        'type': 'Bearish Liquidity Sweep (Inducement)',
                        'level': round(recent_high, 4),
                        'timestamp': candle['timestamp'],
                        'description': 'Harga sweep high lalu balik turun kuat'
                    })
    
    return sweeps[-2:] if sweeps else []


def find_liquidity_zones(df, tolerance=0.003):
    """Cari Liquidity Zones (area di mana banyak stop loss kemungkinan berada)"""
    zones = []
    if len(df) < 40:
        return zones
    
    swings = calculate_swing_points(df)
    highs = swings[swings['swing_high'].notna()]['swing_high'].tolist()
    lows = swings[swings['swing_low'].notna()]['swing_low'].tolist()
    
    all_levels = highs + lows
    
    # Cluster levels yang berdekatan
    all_levels = sorted(all_levels)
    current_cluster = [all_levels[0]]
    
    for level in all_levels[1:]:
        if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
            current_cluster.append(level)
        else:
            if len(current_cluster) >= 2:
                zones.append({
                    'type': 'Liquidity Zone',
                    'low': round(min(current_cluster), 4),
                    'high': round(max(current_cluster), 4),
                    'touches': len(current_cluster),
                    'description': f"Cluster {len(current_cluster)} level (kemungkinan banyak stop)"
                })
            current_cluster = [level]
    
    if len(current_cluster) >= 2:
        zones.append({
            'type': 'Liquidity Zone',
            'low': round(min(current_cluster), 4),
            'high': round(max(current_cluster), 4),
            'touches': len(current_cluster),
            'description': f"Cluster {len(current_cluster)} level"
        })
    
    return zones[-4:] if zones else []


def calculate_setup_score(setup, multi_tf, funding_oi, sweeps, fvg_list, order_blocks, bias, primary_tf='1h'):
    """Advanced Setup Quality Score untuk Grok Crypto Agent (0-100)"""
    score = 45  # base score
    reasons = []
    conviction = "Medium"
    
    # === 1. MULTI-TIMEFRAME CONFLUENCE (Bobot Tertinggi) ===
    conf = multi_tf.get('confluence_score', 50)
    score += (conf - 45) * 0.45   # max ~ +25
    
    if conf >= 85:
        reasons.append("🔥 Konfluensi Multi-TF sangat kuat (4-5 TF align)")
        conviction = "Very High"
    elif conf >= 70:
        reasons.append("✅ Konfluensi Multi-TF bagus")
        conviction = "High"
    elif conf < 55:
        score -= 10
        reasons.append("⚠️ Konfluensi lemah")
    
    # Bonus jika primary TF match dengan higher TF (4H/1D)
    tfs = multi_tf.get('timeframes', {})
    primary_bias = tfs.get(primary_tf, {}).get('bias', '')
    higher_bias = tfs.get('4h', {}).get('bias', '') + tfs.get('1d', {}).get('bias', '')
    if primary_bias and primary_bias in higher_bias:
        score += 8
        reasons.append("Higher TF align dengan primary TF")
    
    # === 2. FUNDING RATE ALIGNMENT ===
    if funding_oi.get('funding_rate') is not None:
        fr = funding_oi['funding_rate']
        direction = setup.get('direction', 'NEUTRAL')
        
        if direction == 'LONG' and fr < -0.01:   # Shorts bayar longs
            score += 10
            reasons.append("Funding negatif → Longs diuntungkan")
        elif direction == 'SHORT' and fr > 0.01:
            score += 10
            reasons.append("Funding positif → Shorts diuntungkan")
        elif abs(fr) > 0.10:
            score -= 12
            reasons.append("Funding ekstrem → risiko tinggi")
    
    # === 3. LIQUIDITY SWEEP / INDUCEMENT (Sinyal Kuat) ===
    if sweeps:
        score += 18
        reasons.append("💧 Liquidity Sweep terdeteksi (inducement kuat)")
        if conviction == "Medium":
            conviction = "High"
    
    # === 4. SMC CONFLUENCE (FVG + Order Block) ===
    has_fvg = len(fvg_list) > 0
    has_ob = len(order_blocks) > 0
    
    if has_fvg and has_ob:
        score += 12
        reasons.append("FVG + Order Block confluence (SMC kuat)")
    elif has_fvg:
        score += 6
        reasons.append("FVG aktif")
    elif has_ob:
        score += 5
    
    # === 5. RISK MANAGEMENT ===
    rr = setup.get('risk_reward', 0)
    if rr >= 3.0:
        score += 10
        reasons.append(f"Excellent Risk-Reward ({rr}:1)")
    elif rr >= 2.0:
        score += 6
        reasons.append(f"Good Risk-Reward ({rr}:1)")
    elif rr < 1.5:
        score -= 8
    
    # === 6. MARKET STRUCTURE STRENGTH ===
    if 'Bullish' in bias or 'Bearish' in bias:
        score += 6
        if 'HH + HL' in bias or 'LH + LL' in bias:
            score += 4
            reasons.append("Market Structure clean & kuat")
    
    # === FINAL ADJUSTMENTS ===
    score = max(25, min(98, int(score)))
    
    if score >= 85:
        conviction = "Very High"
    elif score >= 72:
        conviction = "High"
    elif score >= 58:
        conviction = "Medium"
    else:
        conviction = "Low"
    
    return score, reasons, conviction


# ==================== VISUALISASI CHART ====================

def create_analysis_chart(df, fib_levels, order_blocks, fvg_list, setup, symbol):
    """Buat chart interaktif Plotly dengan semua level"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.7, 0.3],
                        subplot_titles=(f'{symbol} - Price Action + Key Levels', 'Volume'))
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='Price',
        increasing_line_color='#00ff9d',
        decreasing_line_color='#ff4b4b'
    ), row=1, col=1)
    
    # Volume
    colors = ['#00ff9d' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff4b4b' for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df['timestamp'], y=df['volume'],
        marker_color=colors, name='Volume', showlegend=False
    ), row=2, col=1)
    
    current_price = df['close'].iloc[-1]
    
    # Tambah garis Fib
    for name, level in fib_levels.items():
        if 'TP' in name or 'Fib' in name:
            color = '#00b8ff' if 'Fib' in name else '#ffaa00'
            fig.add_hline(y=level, line_dash="dash", line_color=color,
                         annotation_text=name, annotation_position="right",
                         row=1, col=1)
    
    # Order Blocks
    for ob in order_blocks:
        color = 'rgba(0, 255, 157, 0.2)' if 'Demand' in ob['type'] else 'rgba(255, 75, 75, 0.2)'
        fig.add_hrect(y0=ob['low'], y1=ob['high'],
                      fillcolor=color, line_width=0,
                      annotation_text=ob['type'], annotation_position="left",
                      row=1, col=1)
    
    # Fair Value Gaps (FVG)
    for fvg in fvg_list:
        if 'Bullish' in fvg['type']:
            color = 'rgba(0, 200, 100, 0.15)'
            label = "Bullish FVG"
        else:
            color = 'rgba(200, 50, 50, 0.15)'
            label = "Bearish FVG"
        fig.add_hrect(y0=fvg['bottom'], y1=fvg['top'],
                      fillcolor=color, line_width=1, line_color="gray",
                      annotation_text=label, annotation_position="right",
                      row=1, col=1)
    
    # Entry, SL, TP lines
    if setup['direction'] != 'NEUTRAL':
        fig.add_hline(y=setup['entry_zone_low'], line_color="#00ff9d", line_width=2,
                     annotation_text="ENTRY ZONE", annotation_position="left", row=1, col=1)
        fig.add_hline(y=setup['stop_loss'], line_color="#ff4b4b", line_width=2, line_dash="dot",
                     annotation_text="STOP LOSS", annotation_position="left", row=1, col=1)
        fig.add_hline(y=setup['tp1'], line_color="#ffaa00", line_width=1.5, line_dash="dash",
                     annotation_text="TP1", annotation_position="right", row=1, col=1)
        fig.add_hline(y=setup['tp2'], line_color="#ffaa00", line_width=1.5, line_dash="dash",
                     annotation_text="TP2", annotation_position="right", row=1, col=1)
        fig.add_hline(y=setup['tp3'], line_color="#ffaa00", line_width=1.5, line_dash="dash",
                     annotation_text="TP3", annotation_position="right", row=1, col=1)
    
    fig.update_layout(
        height=700,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        title=f"Analisa {symbol} | Bias: {setup['direction']} | Confidence: {setup['confidence']}%"
    )
    
    return fig

# ==================== UI UTAMA ====================

def main():
    st.markdown('<h1 class="main-header">🤖 GROK CRYPTO AGENT v1.5</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Your Personal Smart Money Trading Assistant • Built by GQCoding08</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Pengaturan Screening")
        
        timeframe = st.selectbox(
            "Timeframe Analisa",
            ["5m", "15m", "1h", "4h", "1d"],
            index=2,
            help="Timeframe untuk analisa struktur & Fibonacci"
        )
        
        num_coins = st.slider("Jumlah Koin yang Di-screen", 10, 100, 30, step=5)
        
        st.markdown("---")
        st.subheader("Metode Analisa Aktif")
        st.checkbox("Market Structure (HH/HL & BOS/CHOCH)", value=True, disabled=True)
        st.checkbox("Fibonacci Retracement + Extension", value=True, disabled=True)
        st.checkbox("Supply & Demand + Order Block (SMC)", value=True, disabled=True)
        st.checkbox("Support & Resistance + ATR", value=True, disabled=True)
        
        st.markdown("---")
        
        # ==================== WATCHLIST MANAGER ====================
        st.subheader("📌 My Watchlist")
        
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = []
        
        if 'memory' not in st.session_state:
            st.session_state.memory = []  # Memory Agent: saved setups + notes
        
        # Add coin to watchlist
        add_coin = st.text_input("Tambah koin (contoh: BTC, ETH, SOL)", key="add_watch").upper().strip()
        if st.button("➕ Tambah ke Watchlist") and add_coin:
            if add_coin not in st.session_state.watchlist:
                st.session_state.watchlist.append(add_coin)
                st.success(f"{add_coin} ditambahkan ke watchlist!")
                st.rerun()
        
        # Show current watchlist
        if st.session_state.watchlist:
            st.write("**Koin dalam Watchlist:**")
            for coin in st.session_state.watchlist:
                colw1, colw2 = st.columns([3, 1])
                colw1.write(f"• {coin}")
                if colw2.button("❌", key=f"remove_{coin}"):
                    st.session_state.watchlist.remove(coin)
                    st.rerun()
        
        if st.button("🗑️ Clear Watchlist"):
            st.session_state.watchlist = []
            st.rerun()
        
        st.markdown("---")
        if st.button("🔄 Refresh Data (Clear Cache)", type="secondary"):
            st.cache_data.clear()
            st.rerun()
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Screening Table", "🔍 Detail Analisa per Koin", "📰 News & Sentiment", "🏆 Top Setups Ranking"])
    
    with tab1:
        st.subheader("Daftar Koin Futures + Rekomendasi Singkat")
        
        with st.spinner("Mengambil daftar koin futures & data pasar..."):
            coins_df = get_top_futures_coins(limit=num_coins)
        
        if coins_df.empty:
            st.error("Gagal mengambil data. Coba refresh atau cek koneksi internet.")
            return
        
        st.dataframe(
            coins_df[['symbol', 'name', 'price', 'change_24h', 'volume_24h']].style.format({
                'price': '{:,.2f}',
                'change_24h': '{:+.2f}%',
                'volume_24h': '{:,.0f}'
            }).background_gradient(subset=['change_24h'], cmap='RdYlGn'),
            use_container_width=True,
            height=400
        )
        
        st.info("💡 Pilih koin di tab 'Detail Analisa per Koin' untuk analisa lengkap + chart + level entry/SL/TP")
        
        # ==================== MY WATCHLIST QUICK VIEW ====================
        if st.session_state.get('watchlist'):
            st.markdown("---")
            st.subheader("📌 My Watchlist - Quick Status")
            
            if st.button("🔄 Refresh Watchlist Analysis", key="refresh_watch"):
                watch_data = []
                for coin in st.session_state.watchlist:
                    try:
                        fut_sym = f"{coin}/USDT:USDT"
                        df = fetch_ohlcv(fut_sym, timeframe='1h', limit=50)
                        if df is not None and len(df) > 20:
                            bias, _, _, _ = detect_market_structure(df)
                            multi = analyze_multi_timeframe(fut_sym, primary_tf='1h')
                            funding = get_funding_and_oi(fut_sym)
                            
                            watch_data.append({
                                'Coin': coin,
                                'Bias (1H)': bias,
                                'Confluence': multi['confluence_score'],
                                'Funding %': funding.get('funding_rate', 'N/A'),
                                'Price': round(df['close'].iloc[-1], 2)
                            })
                    except:
                        pass
                
                if watch_data:
                    st.dataframe(pd.DataFrame(watch_data), use_container_width=True, hide_index=True)
                    st.caption("Data di-refresh. Klik koin di tab Detail Analisa untuk analisa lengkap.")
                else:
                    st.warning("Gagal mengambil data watchlist.")
    
    with tab2:
        st.subheader("Analisa Mendalam + Chart Interaktif")
        
        selected_symbol = st.selectbox(
            "Pilih Koin untuk Dianalisa",
            coins_df['symbol'].tolist(),
            index=0
        )
        
        selected_row = coins_df[coins_df['symbol'] == selected_symbol].iloc[0]
        futures_symbol = selected_row['futures_symbol']
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("Harga Saat Ini", f"${selected_row['price']:,.2f}")
            st.metric("24h Change", f"{selected_row['change_24h']:+.2f}%")
            st.metric("24h Volume", f"${selected_row['volume_24h']/1e9:.2f}B")
        
        with col2:
            if st.button(f"🚀 ANALISA LENGKAP {selected_symbol}", type="primary", use_container_width=True):
                with st.spinner(f"🤖 GROK CRYPTO AGENT menganalisa {selected_symbol}... (Structure + FVG + Multi-TF + Liquidity + Scoring)"):
                    df = fetch_ohlcv(futures_symbol, timeframe=timeframe, limit=150)
                    
                    if df is not None and len(df) > 30:
                        current_price = df['close'].iloc[-1]
                        
                        # Analisa
                        bias, structure_notes, swing_h, swing_l = detect_market_structure(df)
                        atr = calculate_atr(df)
                        
                        # Ambil swing terakhir untuk Fib
                        if not swing_h.empty and not swing_l.empty:
                            last_swing_high = swing_h['swing_high'].iloc[-1]
                            last_swing_low = swing_l['swing_low'].iloc[-1]
                            direction = "bullish" if current_price > last_swing_low else "bearish"
                            fib_levels = calculate_fibonacci_levels(last_swing_high, last_swing_low, direction)
                        else:
                            # Fallback
                            recent_high = df['high'].tail(30).max()
                            recent_low = df['low'].tail(30).min()
                            fib_levels = calculate_fibonacci_levels(recent_high, recent_low, "bullish")
                        
                        order_blocks = find_order_blocks(df)
                        fvg_list = detect_fvg(df)
                        sweeps = detect_liquidity_sweep(df)
                        liq_zones = find_liquidity_zones(df)
                        multi_tf = analyze_multi_timeframe(futures_symbol, primary_tf=timeframe)
                        setup = generate_trading_setup(df, current_price, bias, fib_levels, order_blocks, atr)
                        
                        # Tampilkan hasil
                        st.markdown("### 📌 Hasil Analisa Teknis")
                        
                        colA, colB, colC = st.columns(3)
                        colA.metric("Market Bias", bias, delta=setup['direction'])
                        colB.metric("Confidence", f"{setup['confidence']}%")
                        colC.metric("Risk-Reward (TP2)", f"1:{setup['risk_reward']}" if setup['risk_reward'] else "N/A")
                        
                        # Advanced Setup Quality Score
                        adv_score, adv_reasons, conviction = calculate_setup_score(
                            setup, multi_tf, funding_oi, sweeps, fvg_list, order_blocks, bias, primary_tf=timeframe
                        )
                        st.markdown(f"### 🎯 **Setup Quality Score: {adv_score}/100** | Conviction: **{conviction}**")
                        
                        with st.expander("Lihat Breakdown Score"):
                            for r in adv_reasons:
                                st.write(f"• {r}")
                        
                        # ==================== MEMORY AGENT ====================
                        st.markdown("### 🧠 Memory Agent")
                        
                        note = st.text_input("Catatan untuk setup ini (opsional)", key=f"note_{selected_symbol}")
                        
                        if st.button("💾 Save Setup ke Memory", key=f"save_{selected_symbol}"):
                            memory_entry = {
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                'symbol': selected_symbol,
                                'timeframe': timeframe,
                                'bias': bias,
                                'score': adv_score,
                                'conviction': conviction,
                                'direction': setup['direction'],
                                'note': note if note else "No note",
                                'funding_rate': funding_oi.get('funding_rate'),
                                'confluence': multi_tf.get('confluence_score')
                            }
                            st.session_state.memory.append(memory_entry)
                            st.success(f"Setup {selected_symbol} disimpan ke Memory!")
                        
                        # Tampilkan history memory untuk koin ini
                        if st.session_state.memory:
                            similar = [m for m in st.session_state.memory if m['symbol'] == selected_symbol]
                            if similar:
                                with st.expander(f"📜 History Memory untuk {selected_symbol} ({len(similar)}x)"):
                                    for m in similar[-5:]:  # last 5
                                        st.write(f"**{m['timestamp']}** | {m['timeframe']} | Score: {m['score']} | {m['conviction']}")
                                        if m['note'] != "No note":
                                            st.caption(f"Note: {m['note']}")
                        
                        # ==================== SHARE THIS SETUP ====================
                        st.markdown("### 📤 Share This Setup")
                        
                        if st.button("📋 Copy Setup Summary ke Clipboard", key=f"share_{selected_symbol}"):
                            share_text = f"""🤖 GROK CRYPTO AGENT v1.5

Coin: {selected_symbol} | Timeframe: {timeframe}
Bias: {bias} | Direction: {setup['direction']}
Score: {adv_score}/100 | Conviction: {conviction}

Entry Zone: ${setup.get('entry_zone_low', 0):.4f} - ${setup.get('entry_zone_high', 0):.4f}
Stop Loss: ${setup.get('stop_loss', 0):.4f}
TP1: ${setup.get('tp1', 0):.4f} | TP2: ${setup.get('tp2', 0):.4f} | TP3: ${setup.get('tp3', 0):.4f}
Risk-Reward: 1:{setup.get('risk_reward', 0)}

Confluence: {multi_tf.get('confluence_score', 0)}%
Funding Rate: {funding_oi.get('funding_rate', 'N/A')}%

Catatan: {note if note else 'Tidak ada catatan'}

Dianalisa pada {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
                            
                            st.code(share_text, language="text")
                            st.success("✅ Setup summary siap di-copy! Tinggal highlight & Ctrl+C")
                            st.toast("Setup berhasil disiapkan untuk di-share!", icon="📋")
                        
                        # Funding Rate & Open Interest
                        funding_oi = get_funding_and_oi(futures_symbol)
                        if funding_oi.get('funding_rate') is not None:
                            st.markdown("### 💰 Funding Rate & Open Interest (Binance Futures)")
                            colF1, colF2, colF3 = st.columns(3)
                            colF1.metric("Funding Rate", f"{funding_oi['funding_rate']:.4f}%", 
                                        delta="Longs pay Shorts" if funding_oi['funding_rate'] > 0 else "Shorts pay Longs")
                            colF2.metric("Open Interest", f"{funding_oi['open_interest']:,.0f} USDT" if funding_oi['open_interest'] else "N/A")
                            if funding_oi.get('next_funding'):
                                colF3.metric("Next Funding", str(funding_oi['next_funding'])[:16])
                            
                            # Warning jika funding ekstrem
                            if abs(funding_oi['funding_rate']) > 0.05:
                                st.warning("⚠️ Funding Rate ekstrem! Potensi volatility tinggi atau squeeze.")
                        
                        with st.expander("📝 Alasan & Catatan Structure", expanded=True):
                            for note in structure_notes:
                                st.write(f"• {note}")
                            st.write(f"• ATR (14): {atr:.2f}")
                            
                            # FVG Section
                            st.markdown("**Fair Value Gap (FVG) - Smart Money Inefficiency:**")
                            if fvg_list:
                                for fvg in fvg_list[-3:]:
                                    emoji = "🟢" if "Bullish" in fvg['type'] else "🔴"
                                    st.write(f"{emoji} {fvg['type']} | Gap {fvg['gap_pct']}% | Level: ${fvg['bottom']:.4f} - ${fvg['top']:.4f}")
                                st.caption("FVG sering menjadi area support/resistance kuat. Bullish FVG = potensi demand zone.")
                            else:
                                st.write("Tidak ditemukan FVG signifikan pada timeframe ini.")
                        
                        # ==================== MULTI-TIMEFRAME CONFLUENCE ====================
                        with st.expander("📊 Multi-Timeframe Confluence (15m → 1D)", expanded=True):
                            st.markdown(f"**Overall: {multi_tf['overall_bias']}** | Confluence Score: **{multi_tf['confluence_score']}%**")
                            
                            tf_data = []
                            for tf, data in multi_tf['timeframes'].items():
                                tf_data.append({
                                    'Timeframe': tf,
                                    'Bias': data.get('bias', 'N/A'),
                                    'ATR': data.get('atr', 0)
                                })
                            st.dataframe(pd.DataFrame(tf_data), use_container_width=True, hide_index=True)
                            
                            if multi_tf['confluence_score'] >= 80:
                                st.success("🔥 Konfluensi sangat kuat! Setup ini punya kekuatan tinggi.")
                            elif multi_tf['confluence_score'] >= 60:
                                st.info("✅ Konfluensi bagus. Bisa dipertimbangkan.")
                            else:
                                st.warning("⚠️ Konfluensi lemah. Lebih baik tunggu konfirmasi lebih lanjut.")
                        
                        # ==================== LIQUIDITY CONCEPTS ====================
                        with st.expander("💧 Liquidity Sweep & Liquidity Zone (SMC Advanced)", expanded=False):
                            st.markdown("**Liquidity Sweep / Inducement**")
                            if sweeps:
                                for s in sweeps:
                                    st.write(f"• {s['type']} di level ${s['level']} — {s['description']}")
                            else:
                                st.write("Tidak ada Liquidity Sweep signifikan terdeteksi.")
                            
                            st.markdown("**Liquidity Zones** (area potensi stop loss cluster)")
                            if liq_zones:
                                for z in liq_zones:
                                    st.write(f"• {z['description']} | Range: ${z['low']} - ${z['high']}")
                            else:
                                st.write("Belum terbentuk Liquidity Zone yang jelas.")
                        
                        # Trading Setup Box
                        st.markdown("### 🎯 REKOMENDASI SETUP TRADING")
                        if setup['direction'] != 'NEUTRAL':
                            st.success(f"**{setup['direction']} SETUP** | Confidence: {setup['confidence']}%")
                            
                            setup_df = pd.DataFrame({
                                'Parameter': ['Entry Zone', 'Stop Loss', 'Take Profit 1', 'Take Profit 2', 'Take Profit 3', 'Risk : Reward'],
                                'Level': [
                                    f"${setup['entry_zone_low']:.4f} - ${setup['entry_zone_high']:.4f}",
                                    f"${setup['stop_loss']:.4f}",
                                    f"${setup['tp1']:.4f}",
                                    f"${setup['tp2']:.4f}",
                                    f"${setup['tp3']:.4f}",
                                    f"1 : {setup['risk_reward']}"
                                ]
                            })
                            st.dataframe(setup_df, use_container_width=True, hide_index=True)
                            
                            st.markdown("**Alasan Setup:**")
                            for r in setup['reason']:
                                st.write(f"✅ {r}")
                        else:
                            st.warning("Market sedang sideways / tidak ada setup jelas. Tunggu Break of Structure.")
                        
                        # Chart
                        st.markdown("### 📈 Chart Interaktif + Level")
                        fig = create_analysis_chart(df, fib_levels, order_blocks, fvg_list, setup, selected_symbol)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Links
                        st.markdown("### 🔗 Link Cepat untuk Konfirmasi Manual")
                        links = get_news_sentiment(selected_symbol)
                        cols = st.columns(5)
                        for i, (name, url) in enumerate(links.items()):
                            cols[i].link_button(name, url)
                        
                        st.caption("⚠️ Selalu konfirmasi manual di TradingView + perhatikan berita fundamental. Tool ini hanya alat bantu.")
                    else:
                        st.error("Data tidak cukup untuk analisa. Coba timeframe lain atau koin lain.")
    
    with tab3:
        st.subheader("📰 News Sentiment & Sumber Informasi")
        st.info("Untuk sentiment real-time, gunakan link di bawah. Tool ini akan dikembangkan lebih lanjut dengan scraping berita otomatis.")
        
        st.markdown("""
        **Sumber Berita & Sentiment Crypto yang Direkomendasikan:**
        - [CoinPanic](https://coinpanic.com) - News aggregator cepat
        - [Investing.com Crypto](https://www.investing.com/crypto/)
        - [CoinMarketCap News](https://coinmarketcap.com/news/)
        - [Coinglass](https://www.coinglass.com/) - Funding rate & liquidation data (penting untuk futures!)
        - [LunarCrush](https://lunarcrush.com/) - Social sentiment
        - [Santiment](https://santiment.net/) - On-chain + social
        """)
        
        st.warning("Fitur auto sentiment analysis (NLP pada berita) akan ditambahkan di update berikutnya. Beri tahu saya jika prioritas!")
    
    # ==================== TAB 4: TOP SETUPS RANKING ====================
    with tab4:
        st.subheader("🏆 Top Setups Ranking - Grok Crypto Agent")
        st.markdown("Scan pasar dan ranking setup terbaik berdasarkan **Multi-TF Confluence + Funding + Liquidity + SMC**")
        
        col_scan1, col_scan2 = st.columns([2, 1])
        with col_scan1:
            scan_limit = st.slider("Jumlah koin yang di-scan", 10, 40, 20, step=5)
        with col_scan2:
            if st.button("🚀 SCAN MARKET & RANKING", type="primary", use_container_width=True):
                with st.spinner("🔍 GROK CRYPTO AGENT sedang menganalisa pasar... (Multi-TF + Funding + Liquidity + Scoring)"):
                    progress_text = st.empty()
                    progress_text.info("⏳ Mengambil data market + menghitung setup quality. Mohon tunggu...")
                    coins_df = get_top_futures_coins(limit=scan_limit)
                    
                    ranked_setups = []
                    
                    for _, row in coins_df.iterrows():
                        sym = row['symbol']
                        fut_sym = row['futures_symbol']
                        
                        try:
                            # Quick analysis
                            df = fetch_ohlcv(fut_sym, timeframe='1h', limit=60)
                            if df is None or len(df) < 30:
                                continue
                            
                            bias, _, _, _ = detect_market_structure(df)
                            if 'Neutral' in bias or 'Indecisive' in bias:
                                continue  # skip sideways
                            
                            multi = analyze_multi_timeframe(fut_sym, primary_tf='1h')
                            funding = get_funding_and_oi(fut_sym)
                            fvg = detect_fvg(df)
                            ob = find_order_blocks(df)
                            sw = detect_liquidity_sweep(df)
                            
                            # Buat dummy setup untuk scoring
                            dummy_setup = {'direction': 'LONG' if 'Bullish' in bias else 'SHORT', 'risk_reward': 2.2}
                            
                            score, reasons, conviction = calculate_setup_score(
                                dummy_setup, multi, funding, sw, fvg, ob, bias
                            )
                            
                            ranked_setups.append({
                                'Symbol': sym,
                                'Bias': bias,
                                'Score': score,
                                'Conviction': conviction,
                                'Confluence': multi['confluence_score'],
                                'Funding %': funding.get('funding_rate', 0),
                                'Reasons': ' | '.join(reasons[:2]) if reasons else 'Setup standar',
                                'futures_symbol': fut_sym
                            })
                        except:
                            continue
                    
                    if ranked_setups:
                        ranked_df = pd.DataFrame(ranked_setups)
                        ranked_df = ranked_df.sort_values('Score', ascending=False).head(10).reset_index(drop=True)
                        
                        st.success(f"✅ Ditemukan {len(ranked_df)} setup berkualitas tinggi!")
                        st.dataframe(
                            ranked_df[['Symbol', 'Bias', 'Score', 'Conviction', 'Confluence', 'Funding %', 'Reasons']].style.background_gradient(
                                subset=['Score'], cmap='RdYlGn'
                            ),
                            use_container_width=True
                        )
                        
                        st.info("💡 Klik koin di tab 'Detail Analisa per Koin' untuk analisa lengkap + chart.")
                    else:
                        st.warning("Tidak ditemukan setup yang cukup kuat saat ini. Coba scan lagi nanti.")
    
    # Footer
    st.markdown("---")
    st.caption("Dibuat dengan ❤️ oleh **GQCoding08** | Bukan financial advice | Trade responsibly | Update: 27 Mei 2026")

if __name__ == "__main__":
    main()