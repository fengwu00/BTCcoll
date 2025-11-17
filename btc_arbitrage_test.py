import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# ==================== 設定 ====================
CSV_FILE = "btc_arbitrage_log.csv"           # 程式紀錄檔
PLOT_DIR = "arbitrage_plots"                 # 圖表輸出資料夾
os.makedirs(PLOT_DIR, exist_ok=True)

# 真實市場 ID（請自行替換，範例用模擬）
POLY_MARKET_SLUG = "will-bitcoin-exceed-97500-in-next-8-hours"  # Polymarket 市場 slug
LIM_MARKET_ID = "btc-8h-97500"                                 # Limitless 市場 ID

# 套利閾值
SPREAD_THRESHOLD = 0.03  # 3% 價差才算機會
FEE_RATE = 0.015         # 預估總手續費 1.5%

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
        url = f"https://gamma.api.polymarket.com/markets/{POLY_MARKET_SLUG}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            yes_price = float(data.get('yes_bid', 0.5))
            volume = float(data.get('volume', 0))
            return yes_price, volume
    except Exception as e:
        print(f"Polymarket API 錯誤: {e}")
    # 模擬數據（測試用）
    return np.random.uniform(0.45, 0.55), np.random.randint(1000, 10000)

# ==================== 抓 Limitless 價格 ====================
def fetch_lim_price():
    try:
        url = f"https://api.limitless.exchange/v1/markets/{LIM_MARKET_ID}/orderbook"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            book = r.json()
            bids = [float(x[0]) for x in book.get('bids', [])[:5] if x[0]]
            yes_price = np.mean(bids) if bids else 0.5
            volume = float(book.get('volume', 0))
            return yes_price, volume
    except Exception as e:
        print(f"Limitless API 錯誤: {e}")
    # 模擬數據
    return np.random.uniform(0.45, 0.55), np.random.randint(500, 5000)

# ==================== 記錄程式資料 ====================
def record_data():
    poly_yes, poly_vol = fetch_poly_price()
    lim_yes, lim_vol = fetch_lim_price()
    
    spread = abs(poly_yes - lim_yes)
    action = ("BUY POLY YES → SELL LIM YES" if poly_yes < lim_yes 
              else "BUY LIM YES → SELL POLY YES")
    est_profit = max(spread - FEE_RATE, 0) * 100  # 100 股淨利
    
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
    
    # 寫入 CSV
    df = pd.DataFrame([new_row])
    df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    
    status = f"機會" if spread > SPREAD_THRESHOLD else "無機會"
    print(f"[{now.strftime('%H:%M')}] 價差 {spread:.1%} → {status} | 淨利 ${est_profit:.2f}")

# ==================== 生成程式圖表 ====================
def generate_report():
    df = pd.read_csv(CSV_FILE)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    df['minute'] = df['datetime'].dt.minute // 5 * 5  # 每 5 分鐘一格
    
    # 每日熱圖
    for date in df['date'].unique():
        day_df = df[df['date'] == date]
        pivot = day_df.pivot_table(
            index='hour', columns='minute', values='spread', aggfunc='mean'
        )
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(pivot, annot=True, fmt='.1%', cmap='RdYlGn_r', center=SPREAD_THRESHOLD)
        plt.title(f"BTC 套利價差程式熱圖 - {date}\n(每 5 分鐘一格)")
        plt.xlabel("分鐘")
        plt.ylabel("小時")
        plt.tight_layout()
        plt.savefig(f"{PLOT_DIR}/arbitrage_heatmap_{date}.png", dpi=150)
        plt.close()
    
    # 統計報告
    opp = df[df['spread'] > SPREAD_THRESHOLD]
    total_profit = opp['est_profit_100shares'].sum()
    
    print("\n" + "="*50)
    print("程式量化報告")
    print("="*50)
    print(f"總筆數      : {len(df)} 筆")
    print(f"套利機會    : {len(opp)} 次 ({len(opp)/len(df)*100:.1f}%)")
    print(f"平均價差    : {df['spread'].mean():.2%}")
    print(f"最大價差    : {df['spread'].max():.2%}")
    print(f"預估總利潤  : ${total_profit:,.2f} (100 股/次)")
    print(f"圖表已存至  : {PLOT_DIR}/")
    print("="*50)

# ==================== 主程式 ====================
if __name__ == "__main__":
    init_csv()
    print("啟動 BTC 套利程式測試（每 5 分鐘記錄一次）")
    print("按 Ctrl+C 停止並生成報告\n")
    
    try:
        while True:
            record_data()
            time.sleep(300)  # 5 分鐘
    except KeyboardInterrupt:
        print("\n\n停止程式，生成量化報告...")
        generate_report()
