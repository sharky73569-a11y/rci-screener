import os
import time
import datetime
import FinanceDataReader as fdr
import pandas as pd
import pandas_ta as ta
import requests

# 🔒 깃허브 금고(Secrets)에서 안전하게 주소를 불러옵니다. 해킹 위험 0%
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.com/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def main():
    print("▶ 주식 데이터 수집 및 조건 검색을 시작합니다...")
    print("⚠️ 과부하 방지를 위해 종목당 0.3초씩 쉬어갑니다. (약 10~15분 소요)")
    
    df_krx = fdr.StockListing('KRX')
    df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
    
    selected_stocks = []
    
    for index, row in df_krx.iterrows():
        code = row['Code']
        name = row['Name']
        
        time.sleep(0.3) # IP 차단 방지 매너타임
        
        try:
            df = fdr.DataReader(code, periods=50)
            if len(df) < 30: 
                continue
                
            current_price = df['Close'].iloc[-1]
            
            # [조건 1] 주가 범위: 6,000원 이상 ~ 200,000원 미만
            if not (6000 <= current_price < 200000):
                continue
            
            # [조건 2] Williams %R (14) 계산
            williams_r = ta.willr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
            
            # [조건 3] RCI (14) 계산
            period = 14
            if len(df) >= period:
                close_prices = df['Close'].tail(period)
                time_rank = pd.Series(range(1, period + 1), index=close_prices.index)
                price_rank = close_prices.rank(method='min')
                rci = time_rank.corr(price_rank, method='spearman') * 100
            else:
                continue

            # 🎯 요청하신 조건 검증 (RCI -70 이하 / 윌리엄스 -70 ~ -90 사이)
            if rci <= -70 and (-90 <= williams_r <= -70):
                stock_info = f"• *{name}* ({code}): 현재가 {current_price:,.0f}원 (RCI: {rci:.1f}, %R: {williams_r:.1f})"
                selected_stocks.append(stock_info)
                print(f"✨ [종목 발굴] {name} ({code})")
                
        except Exception as e:
            continue

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    if selected_stocks:
        message = f"📅 *{today_str} 조건 검색 결과*\n\n" + "\n".join(selected_stocks)
    else:
        message = f"📅 *{today_str} 조건 검색 결과*\n\n조건에 맞는 종목이 없습니다."
        
    send_telegram_message(message)
    print("🎉 모든 작업 완료!")

if __name__ == "__main__":
    main()
