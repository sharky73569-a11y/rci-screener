import os
import time
import datetime
import FinanceDataReader as fdr
import pandas as pd
import requests

# 🔒 깃허브 금고(Secrets) 연동
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.com/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        print(f"텔레그램 서버 응답: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"텔레그램 전송 예외 발생: {e}")

# 🛠️ Williams %R 자체 계산 함수 (오타 완벽 수정)
def calculate_williams_r(df, period=14):
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()
    williams_r = ((high_max - df['Close']) / (high_max - low_min)) * -100
    return williams_r.iloc[-1]

# 🛠️ RCI 자체 계산 함수
def calculate_rci(df, period=14):
    if len(df) < period:
        return None
    close_prices = df['Close'].tail(period)
    time_rank = pd.Series(range(1, period + 1), index=close_prices.index)
    price_rank = close_prices.rank(method='min')
    rci = time_rank.corr(price_rank, method='spearman') * 100
    return rci

def main():
    print("▶ 주식 데이터 수집 및 조건 검색을 시작합니다...")
    print("⚠️ 과부하 방지를 위해 종목당 0.3초씩 쉬어갑니다. (약 10~15분 소요)")
    
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
    except Exception as e:
        print(f"KRX 종목 리스트 수집 실패: {e}")
        return
    
    selected_stocks = []
    count = 0
    
    for index, row in df_krx.iterrows():
        code = row['Code']
        name = row['Name']
        
        time.sleep(0.3) # IP 차단 방지 매너타임
        
        try:
            df = fdr.DataReader(code, index.date() - datetime.timedelta(days=60) if hasattr(index, 'date') else None)
            # 안전하게 최근 40거래일 데이터 확보
            df = df.tail(40)
            if len(df) < 20: 
                continue
                
            current_price = df['Close'].iloc[-1]
            
            # [조건 1] 주가 범위: 6,000원 이상 ~ 200,000원 미만
            if not (6000 <= current_price < 200000):
                continue
            
            # [조건 2] Williams %R 및 RCI 계산
            williams_r = calculate_williams_r(df, 14)
            rci = calculate_rci(df, 14)
            
            if rci is None or pd.isna(williams_r) or pd.isna(rci):
                continue

            count += 1
            if count % 500 == 0:
                print(f" 진행 중... ({count}개 종목 검사 완료)")

            # 🎯 요청하신 바닥 조건 검증 (RCI -70 이하 / 윌리엄스 -70 ~ -90 사이)
            if rci <= -70 and (-90 <= williams_r <= -70):
                stock_info = f"• *{name}* ({code}): 현재가 {current_price:,.0f}원 (RCI: {rci:.1f}, %R: {williams_r:.1f})"
                selected_stocks.append(stock_info)
                print(f"✨ [종목 발굴] {name} ({code})")
                
        except Exception as e:
            continue

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    if selected_stocks:
        message = f"📅 *{today_str} RCI 바닥 조건 검색 결과*\n\n" + "\n".join(selected_stocks)
    else:
        message = f"📅 *{today_str} RCI 바닥 조건 검색 결과*\n\n조건에 맞는 바닥 종목이 오늘 시장에 없습니다."
        
    print("▶ 텔레그램으로 결과를 전송합니다...")
    send_telegram_message(message)
    print("🎉 모든 작업 완료!")

if __name__ == "__main__":
    main()
