import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# ==================== 設定 ====================
CSV_FILE = "btc_arbitrage_log.csv"
PLOT_DIR = "arbitrage_plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# 真實市場 ID（替換成當前 BTC 市場，例如從 Polymarket 複製）
POLY_MARKET_SLUG = "bitcoin-price-prediction-8h"  # 示例：Polymarket BTC 市場 slug
LIM_MARKET_ID = "btc-8h-prediction"                # 示例：Limitless 市場 ID

SPREAD_THRESHOLD = 0.03  # 3% 價差
FEE_RATE = 0.015         # 1.5% 手續費

# ==================== 初始化 CSV ====================
def init_csv():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=[
            'timestamp', 'datetime', 'poly_yes', 'lim_yes', 'spread',
            'action', 'est_profit_100shares', 'poly_volume', 'lim_volume'
        ])
        df.to_csv(CSV_FILE, index=False)
        print(f"程式初始化：{CSV_FILE} 建立完成")

# ==================== 抓 Polymarket 價格 ====================
def fetch_poly_price():
    try:
        url = f"https://gamma.api.polymarket.com/markets?slug={POLY_MARKET_SLUG}&active=true"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get('markets', [{}])[0]
            yes_price = float(data.get('yes_bid', 0.5))
            volume = float(data.get('volume', 0))
            return yes_price, volume
    except Exception as e:
        print(f"Polymarket API 錯誤: {e}")
    # 模擬（測試用）
    return np.random.uniform(0.45, 0.55), np.random.randint(1000, 10000)

# ==================== 抓 Limitless 價格 ====================
def fetch_lim_price():
    try:
        url = f"https://api.limitless.exchange/v1/markets/{LIM_MARKET_ID}/orderbook"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            book = r.json()
            bids = [float(x[0]) for x in book.get('bids', [])[:5] if len(x) > 0 and x[0]]
            yes_price = np.mean(bids) if bids else 0.5
            volume = float(book.get('volume', 0))
            return yes_price, volume
    except Exception as e:
        print(f"Limitless API 錯誤: {e}")
    # 模擬
    return np.random.uniform(0.45, 0.55), np.random.randint(500, 5000)

# ==================== 記錄資料 ====================
def record_data():
    poly_yes, poly_vol = fetch_poly_price()
    lim_yes, lim_vol = fetch_lim_price()
    
    spread = abs(poly_yes - lim_yes)
    action = ("BUY POLY YES → SELL LIM YES" if poly_yes < lim_yes 
              else "BUY LIM YES → SELL POLY YES")
    est_profit = max(spread - FEE_RATE, 0) * 100
    
    now = datetime.now()
    new_row = {
        'timestamp': now.isoformat(),
        'datetime': now.strftime("%Y-%m-%d %H:%M"),
        'poly_yes': round(poly_yes, 4),
        'lim_yes': round(lim_yes, 4),
        'spread': round(spread, 4),
        'action': action if spread > SPREAD_THRESHOLD else "NO ARB",
        'est_profit_100shares': round(est_profit, 2),
        'poly_volume': int(poly_vol),
        'lim_volume': int(lim_vol)
    }
    
    df = pd.DataFrame([new_row])
    df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    
    status = f"機會" if spread > SPREAD_THRESHOLD else "無機會"
    print(f"[{now.strftime('%H:%M')}] 價差 {spread:.1%} → {status} | 淨利 ${est_profit:.2f}")

# ==================== 生成報告 ====================
def generate_report():
    df = pd.read_csv(CSV_FILE)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    
    # 熱圖
    for date in df['date'].unique():
        day_df = df[df['date'] == date]
        pivot = day_df.pivot_table(index='hour', values='spread', aggfunc='mean')
        
        plt.figure(figsize=(10, 6))
        sns.heatmap(pivot.to_frame().T, annot=True, fmt='.1%', cmap='RdYlGn_r', center=SPREAD_THRESHOLD)
        plt.title(f"BTC 套利價差熱圖 - {date}")
        plt.xlabel("小時")
        plt.tight_layout()
        plt.savefig(f"{PLOT_DIR}/heatmap_{date}.png", dpi=150)
        plt.close()
    
    # 統計
    opp = df[df['spread'] > SPREAD_THRESHOLD]
    total_profit = opp['est_profit_100shares'].sum()
    print(f"\n程式報告：總機會 {len(opp)} 次 | 平均價差 {df['spread'].mean():.2%} | 總利潤 ${total_profit:,.2f}")

# ==================== 主程式（每小時跑） ====================
if __name__ == "__main__":
    init_csv()
    print("啟動 BTC 套利測試程式（每小時記錄）")
    
    while True:
        if datetime.now().minute == 0:  # 只在整點跑
            record_data()
            generate_report()  # 每小時生成報告
        time.sleep(60)
