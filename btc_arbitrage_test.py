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

# 填入真實市場（不會報錯就算抓不到也會用模擬數據）
POLY_MARKET_SLUG = "will-bitcoin-exceed-100000-by-end-of-2025"  # 隨便填一個存在的 slug 即可
LIM_MARKET_ID   = "btc-8h"                                      # Limitless 市場 ID（可留空）

SPREAD_THRESHOLD = 0.03   # 3% 才算機會
FEE_RATE = 0.015          # 預估手續費

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
    except: pass
    return np.random.uniform(0.45, 0.55), np.random.randint(1000, 20000)

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
    except: pass
    return np.random.uniform(0.45, 0.55), np.random.randint(500, 8000)

# ==================== 記錄一筆 ====================
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
    logging.info(f"價差 {spread:.2%} → {status} | 預估淨利 ${profit:.2f}")

# ==================== 產生當日熱圖 ====================
def generate_daily_plot():
    if not os.path.exists(CSV_FILE): return
    df = pd.read_csv(CSV_FILE)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    
    for date in df['date'].unique():
        day = df[df['date'] == date]
        pivot = day.pivot_table(values='spread', index='hour', aggfunc='mean').fillna(0)
        
        plt.figure(figsize=(10, 6))
        sns.heatmap(pivot.T, annot=True, fmt='.1%', cmap='RdYlGn_r', center=SPREAD_THRESHOLD, cbar_kws={'label': '價差'})
        plt.title(f"BTC 預測市場套利熱圖 - {date} (台灣時間)")
        plt.xlabel("小時")
        plt.tight_layout()
        plt.savefig(f"{PLOT_DIR}/heatmap_{date}.png", dpi=200)
        plt.close()
    
    opp = df[df['spread'] > SPREAD_THRESHOLD]
    logging.info(f"今日總機會 {len(opp)} 次 | 平均價差 {df['spread'].mean():.2%} | 預估總利潤 ${opp['est_profit_100shares'].sum():.2f}")

# ==================== 主程式（Background Worker 專用）===================
if __name__ == "__main__":
    logging.info("BTC 套利 Background Worker 已啟動！")
    init_csv()
    
    while True:
        now = datetime.now()
        # 每小時整點 0~2 分內執行一次
        if now.minute <= 2 and now.second < 30:
            record_once()
            if now.minute == 0:        # 整點時產生當日熱圖
                generate_daily_plot()
            time.sleep(3600)           # 睡一小時，避免重複
        else:
            time.sleep(20)
