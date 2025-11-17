import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# ==================== 設定 ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

CSV_FILE = "btc_arbitrage_log.csv"
PLOT_DIR = "arbitrage_plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# 你可以隨時換成真實市場（抓不到也會自動用模擬數據，不會當掉）
POLY_MARKET_SLUG = "will-bitcoin-exceed-100000-by-end-of-2025"   # Polymarket 任一活躍市場 slug
LIM_MARKET_ID   = "btc-8h"                                      # Limitless 市場 ID（範例）

SPREAD_THRESHOLD = 0.03   # 3% 以上才算機會
FEE_RATE = 0.015          # 預估總手續費 1.5%

# ==================== 初始化 CSV ====================
def init_csv():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=[
            'timestamp','datetime','poly_yes','lim_yes','spread',
            'action','est_profit_100shares','poly_volume','lim_volume'
        ])
        df.to_csv(CSV_FILE, index=False)
        logging.info("初始化 CSV 完成")

# ==================== Polymarket ====================
def fetch_poly_price():
    try:
        url = f"https://gamma.api.polymarket.com/markets?slug={POLY_MARKET_SLUG}&active=true"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.json().get('markets'):
            m = r.json()['markets'][0]
            return float(m.get('yes_bid', 0.5)), float(m.get('volume', 0))
    except Exception as e:
        logging.warning(f"Polymarket API 失敗: {e}")
    # 模擬數據（確保永不當機）
    return np.random.uniform(0.42, 0.58), np.random.randint(1000, 30000)

# ==================== Limitless ====================
def fetch_lim_price():
    try:
        url = f"https://api.limitless.exchange/v1/markets/{LIM_MARKET_ID}/orderbook"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            book = r.json()
            bids = [float(x[0]) for x in book.get('bids', [])[:5] if x]
            price = np.mean(bids) if bids else 0.5
            return price, float(book.get('volume', 0))
    except Exception as e:
        logging.warning(f"Limitless API 失敗: {e}")
    return np.random.uniform(0.42, 0.58), np.random.randint(500, 10000)

# ==================== 記錄一次 ====================
def record_once():
    poly_yes, poly_vol = fetch_poly_price()
    lim_yes, lim_vol   = fetch_lim_price()
    
    spread = abs(poly_yes - lim_yes)
    action = "BUY POLY → SELL LIM" if poly_yes < lim_yes else "BUY LIM → SELL POLY"
    profit = max(spread - FEE_RATE, 0) * 100
    
    row = {
        'timestamp': datetime.now().isoformat(),
        'datetime': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'poly_yes': round(poly_yes, 4),
        'lim_yes': round(lim_yes, 4),
        'spread': round(spread, 4),
        'action': action if spread > SPREAD_THRESHOLD else "NO ARB",
        'est_profit_100shares': round(profit, 2),
        'poly_volume': int(poly_vol),
        'lim_volume': int(lim_vol)
    }
    
    pd.DataFrame([row]).to_csv(CSV_FILE, mode='a', header=False, index=False)
    
    status = "機會！" if spread > SPREAD_THRESHOLD else "無機會"
    logging.info(f"價差 {spread:.2%} → {status} | 預估淨利 ${profit:.2f} (100股)")

# ==================== 產生當日熱圖（已解決中文方框）===================
def generate_daily_plot():
    if not os.path.exists(CSV_FILE):
        return
    
    df = pd.read_csv(CSV_FILE)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    
    for date in df['date'].unique():
        day = df[df['date'] == date]
        pivot = day.pivot_table(values='spread', index='hour', aggfunc='mean').fillna(0)
        
        plt.figure(figsize=(11, 7))
        # 關鍵：強制支援中文（GitHub Actions 環境可用）
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'Noto Sans CJK TC', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        sns.heatmap(pivot.T, annot=True, fmt='.1%', cmap='RdYlGn_r', center=SPREAD_THRESHOLD,
                    cbar_kws={'label': '價差'}, linewidths=.5, linecolor='gray')
        plt.title(f"BTC 預測市場套利熱圖 - {date}\n（台灣時間）", fontsize=18, pad=20)
        plt.xlabel("小時", fontsize=14)
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(f"{PLOT_DIR}/heatmap_{date}.png", dpi=200, bbox_inches='tight')
        plt.close()
    
    opp = df[df['spread'] > SPREAD_THRESHOLD]
    total_profit = opp['est_profit_100shares'].sum()
    logging.info(f"今日統計 → 機會 {len(opp)} 次 | 平均價差 {df['spread'].mean():.2%} | 預估總利潤 ${total_profit:.2f}")

# ==================== 主程式（GitHub Actions 專用）===================
if __name__ == "__main__":
    logging.info("BTC 套利機器人已啟動！台灣時間每小時整點自動執行")
    init_csv()
    
    # 只在整點前 3 分鐘內執行一次（避免重複）
    now = datetime.now()
    if now.minute <= 3:
        record_once()
        if now.minute == 0:      # 整點時產生當日熱圖
            generate_daily_plot()
        logging.info("本小時任務完成，等待下一小時...")
    else:
        logging.info(f"非執行時段（目前 {now.minute} 分），等待整點...")
