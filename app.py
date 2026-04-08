import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import time
import requests
import re
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 윈도우 전용 알람 라이브러리 (서버 에러 방지)
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="LazyDog TV Sync Hunter v12 (실전 샌드위치 패치)", layout="wide")
st.title(" 🎯 LazyDog: Pine Script Sync Hunter v12 (매복 특화)")
st.markdown("""
### ⚡ 멀티 타임프레임 고속 스캔 (모바일 지원)
**업데이트:** [🥪 샌드위치 대기] 로직이 '급등 ➡️ 도지(눌림)' 상태인 실전 매복 타점을 잡아내도록 수정되었습니다.
""")

# ==========================================
# 1.5. 실시간 원유 차트 & 경제 뉴스 헤드라인
# ==========================================
@st.cache_data(ttl=60)
def get_dashboard_data():
    oil_data = {"price": 0.0, "change": 0.0, "pct": 0.0, "history": None}
    kr_news = []
    global_news = []

    try:
        wti = yf.Ticker("CL=F").history(period="1d", interval="5m")
        if not wti.empty and len(wti) >= 2:
            prev_close = wti['Close'].iloc[0]
            curr_price = wti['Close'].iloc[-1]
            oil_data["price"] = curr_price
            oil_data["change"] = curr_price - prev_close
            oil_data["pct"] = (oil_data["change"] / prev_close) * 100
            oil_data["history"] = wti['Close']
        elif len(wti) == 1:
            oil_data["price"] = wti['Close'].iloc[-1]
            oil_data["history"] = wti['Close']
    except:
        pass

    def parse_pubdate(pubdate_str):
        try:
            parsed_date = email.utils.parsedate_to_datetime(pubdate_str)
            return parsed_date.strftime("%m-%d %H:%M")
        except:
            return ""

    try:
        kr_root = ET.fromstring(requests.get("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko").content)
        for item in kr_root.findall('.//item')[:4]:
            title = item.find('title').text
            pubdate = parse_pubdate(item.find('pubDate').text)
            kr_news.append({"title": title, "date": pubdate})
        
        us_root = ET.fromstring(requests.get("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en").content)
        for item in us_root.findall('.//item')[:4]:
            title = item.find('title').text
            pubdate = parse_pubdate(item.find('pubDate').text)
            global_news.append({"title": title, "date": pubdate})
    except:
        kr_news = [{"title": "경제 뉴스 로딩 실패", "date": ""}]
        global_news = [{"title": "경제 뉴스 로딩 실패", "date": ""}]

    return oil_data, kr_news, global_news

oil_data, kr_news, global_news = get_dashboard_data()

st.divider()
col1, col2, col3 = st.columns([1, 1.5, 1.5])

with col1:
    st.subheader("🛢️ WTI 원유 (Today)")
    if oil_data['price']:
        color = "normal" if oil_data['change'] > 0 else "inverse"
        sign = "+" if oil_data['change'] > 0 else ""
        st.metric(
            label="Crude Oil (USD/bbl)",
            value=f"${oil_data['price']:.2f}",
            delta=f"{sign}{oil_data['change']:.2f} ({sign}{oil_data['pct']:.2f}%)",
            delta_color=color
        )
        if oil_data['history'] is not None:
            st.line_chart(oil_data['history'], height=150)
    else:
        st.write("데이터 로딩 중...")

with col2:
    st.subheader("🇰🇷 실시간 국내 경제 뉴스")
    for n in kr_news:
        date_str = f"**[{n['date']}]** " if n['date'] else ""
        st.markdown(f"- {date_str}{n['title']}")

with col3:
    st.subheader("🌎 실시간 월스트리트 뉴스")
    for n in global_news:
        date_str = f"**[{n['date']}]** " if n['date'] else ""
        st.markdown(f"- {date_str}{n['title']}")

st.divider()

# ==========================================
# 1.8. 포트폴리오 종목 분석 AI
# ==========================================
st.subheader("🤖 포트폴리오 다중 종목 분석 AI")
st.markdown("내 포트폴리오 종목을 입력하고 일괄 분석하세요. **(한국 주식은 '삼성전자' 등 이름 입력 가능! 미장은 'AAPL' 등 티커 입력)**")

@st.cache_data
def get_krx_mapping():
    try:
        df = fdr.StockListing('KRX')
        return df[['Code', 'Name', 'Market']]
    except:
        return pd.DataFrame()

krx_df = get_krx_mapping()

def get_stock_news(query, limit=3):
    url = f"https://news.google.com/rss/search?q={query}+when:7d&hl=ko&gl=KR&ceid=KR:ko"
    bad_keywords = ['하락', '급락', '악재', '적자', '소송', '매도', '우려', '리스크', '감소', '위기', '폭락', '수사', '패소', '목표가 하향', '지연', '부진']
    news_items = []
    
    try:
        res = requests.get(url, timeout=3)
        root = ET.fromstring(res.content)
        for item in root.findall('.//item')[:limit]:
            title = item.find('title').text
            pubdate = item.find('pubDate').text
            
            try:
                dt = email.utils.parsedate_to_datetime(pubdate)
                date_str = dt.strftime("%m-%d %H:%M")
            except:
                date_str = ""
            
            sentiment = "강세"
            color = "#089981"
            for bw in bad_keywords:
                if bw in title:
                    sentiment = "약세"
                    color = "#f23645"
                    break
            
            news_items.append({"title": title, "date": date_str, "sentiment": sentiment, "color": color})
    except:
        pass
    
    if not news_items:
        news_items.append({"title": f"최근 7일 내 '{query}' 관련 주요 뉴스가 없습니다.", "date": "", "sentiment": "중립", "color": "#8b94a5"})
        
    return news_items

if 'portfolio_df' not in st.session_state:
    st.session_state.portfolio_df = pd.DataFrame([
        {"종목명/코드": "대덕전자", "평단가": 64600.0, "수량": 8.0},
        {"종목명/코드": "이수스페셜티케미컬", "평단가": 101880.0, "수량": 5.0},
        {"종목명/코드": "AAPL", "평단가": 170.0, "수량": 25.0}
    ])

edited_df = st.data_editor(
    st.session_state.portfolio_df, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "종목명/코드": st.column_config.TextColumn("종목명/코드 (예: 삼성전자, AAPL)", required=True),
        "평단가": st.column_config.NumberColumn("평단가 (원/달러)", min_value=0.0, step=100.0),
        "수량": st.column_config.NumberColumn("수량 (주)", min_value=0.0, step=1.0),
    }
)

if st.button("포트폴리오 일괄 분석하기", use_container_width=True):
    st.markdown("### 📊 포트폴리오 진단 결과")
    card_cols = st.columns(2)
    
    for idx, row in edited_df.iterrows():
        raw_input = str(row.get("종목명/코드", "")).strip()
        if not raw_input or raw_input == "nan":
            continue
            
        avg_price = float(row.get("평단가", 0.0))
        quantity = float(row.get("수량", 0.0))
        
        target_ticker = raw_input.upper()
        display_name = raw_input
        kr_code = ""
        
        if not krx_df.empty:
            name_match = krx_df[krx_df['Name'] == raw_input]
            if not name_match.empty:
                kr_code = name_match.iloc[0]['Code']
                market = name_match.iloc[0]['Market']
                target_ticker = f"{kr_code}.KS" if market in ['KOSPI', 'KOSPI200'] else f"{kr_code}.KQ"
                display_name = raw_input
            elif target_ticker.isdigit() and len(target_ticker) == 6:
                code_match = krx_df[krx_df['Code'] == target_ticker]
                kr_code = target_ticker
                if not code_match.empty:
                    market = code_match.iloc[0]['Market']
                    display_name = code_match.iloc[0]['Name']
                    target_ticker = f"{kr_code}.KS" if market in ['KOSPI', 'KOSPI200'] else f"{kr_code}.KQ"
                else:
                    target_ticker += ".KS"
        elif target_ticker.isdigit() and len(target_ticker) == 6:
            kr_code = target_ticker
            target_ticker += ".KS"

        current_price = 0.0
        try:
            if kr_code:
                df_price = fdr.DataReader(kr_code)
                if not df_price.empty:
                    current_price = df_price['Close'].iloc[-1]
            else:
                yf_price = yf.Ticker(target_ticker).history(period="5d")
                if not yf_price.empty:
                    current_price = yf_price['Close'].iloc[-1]
        except:
            pass
            
        if current_price == 0.0 and avg_price > 0:
            current_price = avg_price

        roi = 0.0
        if avg_price > 0 and current_price > 0:
            roi = ((current_price - avg_price) / avg_price) * 100

        if roi >= 5.0:
            action_text = "차익실현 고려"
            action_color = "#f23645"
            action_bg = "rgba(242, 54, 69, 0.05)"
        elif roi <= -5.0:
            action_text = "비중축소 고려"
            action_color = "#2962ff"
            action_bg = "rgba(41, 98, 255, 0.05)"
        else:
            action_text = "보유 유지 (Hold)"
            action_color = "#089981"
            action_bg = "rgba(8, 153, 129, 0.05)"
            
        display_code = target_ticker.replace(".KS", "").replace(".KQ", "")
        display_price = f"{current_price:,.0f}" if current_price > 1000 else f"{current_price:,.2f}"
        display_roi = f"▲{roi:.2f}%" if roi > 0 else f"▼{abs(roi):.2f}%" if roi < 0 else "0.00%"
        roi_txt_color = "#f23645" if roi > 0 else "#2962ff" if roi < 0 else "#8b94a5"
        
        summary_text = f"현재 시장가 {display_price} 기준, 내 포트폴리오 수익률은 {display_roi} 입니다."
        
        recent_news = get_stock_news(display_name, limit=3)
        bullets_html = ""
        for n in recent_news:
            date_tag = f" <span style='color:#8b94a5; font-size:11px; margin-left:4px;'>({n['date']})</span>" if n['date'] else ""
            bullets_html += f"""
            <div style="display: flex; gap: 8px; align-items: flex-start;">
                <span style="color: {n['color']}; font-weight: 700;">● [{n['sentiment']}]</span>
                <span style="font-weight: 500;">{n['title']}{date_tag}</span>
            </div>
            """

        raw_html = f"""
        <div style="background-color: #1e222d; border-radius: 12px; padding: 24px; color: #e2e8f0; font-family: 'Malgun Gothic', dotum, sans-serif; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #2b313f; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <span style="font-size: 20px; font-weight: 800; color: #ffffff;">{display_name}</span>
                        <span style="font-size: 14px; font-weight: 600; color: #8b94a5;">{display_code} | 내 포지션</span>
                    </div>
                    <div style="font-size: 12px; color: #8b94a5;">수량: {quantity}주 | 평단: {avg_price:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 20px; font-weight: 800; color: #ffffff;">{display_price}</div>
                    <div style="font-size: 14px; font-weight: 700; color: {roi_txt_color};">{display_roi}</div>
                </div>
            </div>
            <div style="background-color: #131722; border-left: 4px solid #2962ff; border-radius: 4px; padding: 12px; margin-bottom: 20px; font-size: 13px; color: #b2b5be; line-height: 1.5; font-weight: 500;">
                {summary_text}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px;">
                <div>
                    <div style="font-size: 12px; color: #8b94a5; margin-bottom: 6px;">뉴스 감성</div>
                    <div style="font-size: 15px; font-weight: 700; color: #ffffff;">실시간</div>
                </div>
                <div>
                    <div style="font-size: 12px; color: #8b94a5; margin-bottom: 6px;">소셜 감성</div>
                    <div style="font-size: 15px; font-weight: 700; color: #ffffff;">연동됨</div>
                </div>
                <div>
                    <div style="font-size: 12px; color: #8b94a5; margin-bottom: 6px;">리스크</div>
                    <div style="font-size: 15px; font-weight: 700; color: #ff9800;">변동성</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 12px; color: #8b94a5; margin-bottom: 6px; padding-right: 4px;">권장 액션</div>
                    <div style="border: 1px solid {action_color}; border-radius: 16px; padding: 5px 12px; font-size: 13px; font-weight: 600; color: {action_color}; display: inline-flex; align-items: center; gap: 6px; background-color: {action_bg};">
                        <div style="width: 8px; height: 8px; background-color: {action_color}; border-radius: 50%; box-shadow: 0 0 4px {action_color};"></div>
                        {action_text}
                    </div>
                </div>
            </div>
            <hr style="border: none; border-top: 1px solid #2a2e39; margin: 20px 0;">
            <div style="font-size: 12px; color: #8b94a5; margin-bottom: 16px; display: flex; align-items: center; gap: 6px;">
                <span style="font-size: 14px;">📰</span> 실시간 주요 헤드라인 (최근 7일)
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px; color: #b2b5be;">
                {bullets_html}
            </div>
        </div>
        """
        safe_html = "".join([line.strip() for line in raw_html.split('\n')])
        with card_cols[idx % 2]:
            st.markdown(safe_html, unsafe_allow_html=True)

st.divider()

# ==========================================
# 2. 데이터 수집
# ==========================================
@st.cache_data
def get_stock_list_final(market_name, scan_limit):
    results = []
    kr_garbage = [
        'KODEX', 'TIGER', 'ACE', 'KBSTAR', 'HANARO', 'SOL', 'KOSEF', 'ARIRANG', 
        'TIMEFOLIO', 'KOACT', 'WOORI', 'PLUS', 'MASTER', 'HK', 'FOCUS', 'RISE', 
        'KIWOOM', '1Q', 'WON', 'HERO', 'UNICORN', 'MIGHTY', 'QV',
        'ETN', 'ETF', '스팩', 'SPAC', '인수목적', '전환', '선물', '채권', 
        '레버리지', '인버스', '배당', '커버드콜', '리츠', 'REITS', '인프라', 
        '선박', '투자', '펀드', '지주', '홀딩스'
    ]
    us_garbage = [
        'ETF', 'ETN', 'Acquisition', 'SPAC', 'Fund', 'Trust', 'REIT', 
        'Bull', 'Bear', '2X', '3X', 'Ultra', 'Short', 'ProShares', 
        'Direxion', 'Vanguard', 'iShares', 'Invesco', 'Global X', 'Schwab', 'First Trust'
    ]

    if "S&P" in market_name or "NASDAQ" in market_name or "Russell" in market_name:
        try:
            if "S&P" in market_name:
                df = fdr.StockListing('S&P500')
            elif "Russell" in market_name:
                df = fdr.StockListing('NYSE')
            else:
                df = fdr.StockListing('NASDAQ')
                
            col_map = {c.lower(): c for c in df.columns}
            if 'marcap' in col_map:
                df = df.sort_values(by=col_map['marcap'], ascending=False)
            elif 'marketcap' in col_map:
                df = df.sort_values(by=col_map['marketcap'], ascending=False)
                
            if scan_limit != "전체 (All)":
                df = df.head(int(scan_limit))
                
            for idx, row in df.iterrows():
                ticker = str(row.get('Symbol', row.get('Code', '')))
                name = row.get('Name', ticker)
                is_garbage = any(kw.lower() in name.lower() for kw in us_garbage)
                if not is_garbage:
                    results.append({"code": ticker, "name": name})
            return results
        except:
            return [{"code": "AAPL", "name": "Apple (Error Load)"}]

    market_code = "0" if "KOSPI" in market_name else "1"
    suffix = ".KS" if "KOSPI" in market_name else ".KQ"
    max_page = 35 if scan_limit == "전체 (All)" else (int(scan_limit) // 50) + 2
    limit_num = 100000 if scan_limit == "전체 (All)" else int(scan_limit)

    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        count = 0
        for page in range(1, max_page + 1):
            if count >= limit_num: break
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={market_code}&page={page}"
            res = requests.get(url, headers=headers, timeout=5)
            html = res.content.decode('euc-kr', 'replace')
            matches = re.findall(r'href="/item/main\.naver\?code=(\d{6})".*?>(.*?)</a>', html)
            
            if not matches: break
            for code, name in matches:
                if count >= limit_num: break
                name = name.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                is_garbage = any(kw in name.upper() for kw in kr_garbage) or name.endswith('우') or name.endswith('우B') or '우(' in name
                
                if not is_garbage:
                    results.append({"code": code + suffix, "name": name})
                    count += 1
        return results
    except:
        return []

# ==========================================
# 3. 자체 내장 보조지표 함수
# ==========================================
def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_supertrend(df, period=10, multiplier=3.0):
    hl2 = (df['High'] + df['Low']) / 2
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    ub = hl2 + (multiplier * atr)
    lb = hl2 - (multiplier * atr)
    
    close_list = df['Close'].tolist()
    ub_list = ub.tolist()
    lb_list = lb.tolist()
    dir_list = [1] * len(df)
    
    for i in range(1, len(df)):
        if pd.isna(close_list[i]) or pd.isna(ub_list[i-1]):
            continue
        if close_list[i] > ub_list[i-1]:
            dir_list[i] = 1
        elif close_list[i] < lb_list[i-1]:
            dir_list[i] = -1
        else:
            dir_list[i] = dir_list[i-1]
            if dir_list[i] == 1:
                lb_list[i] = max(lb_list[i], lb_list[i-1])
            else:
                ub_list[i] = min(ub_list[i], ub_list[i-1])
                
    return dir_list

# ==========================================
# 4. 분석 로직
# ==========================================
def analyze_stock(ticker_info, timeframe):
    ticker = ticker_info['code']
    name = ticker_info['name']
    
    result = {"sniper": None, "entry": None, "touch": None, "surge_prep": None, "sandwich": None}
    
    try:
        if timeframe == "1D":
            df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True, threads=False)
        else:
            df = yf.download(ticker, period="730d", interval="1h", progress=False, auto_adjust=True, threads=False)

        if df.empty or len(df) < 80: return result

        if isinstance(df.columns, pd.MultiIndex):
            try: df.columns = df.columns.get_level_values(0)
            except: pass

        if timeframe == "4H":
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            aggregation = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
            if 'Volume' not in df.columns: del aggregation['Volume']
            df = df.resample('4h').agg(aggregation).dropna()

        if len(df) < 60 or 'Close' not in df.columns: return result

        df['EMA5'] = calc_ema(df['Close'], 5)
        df['EMA20'] = calc_ema(df['Close'], 20)
        df['EMA60'] = calc_ema(df['Close'], 60)
        df['EMA200'] = calc_ema(df['Close'], 200)
        df['RSI'] = calc_rsi(df['Close'], 14)
        df['stDir'] = calc_supertrend(df, 10, 3.0)

        # === 샌드위치 (도지 매복 대기) 로직 ===
        # 어제(d1)는 장대양봉(7% 이상), 오늘(d0)은 도지(몸통 3% 이하)이면서 어제 중심선 위에서 가격 방어
        try:
            d0, d1 = df.iloc[-1], df.iloc[-2]
            
            rise_d1 = (d1['Close'] - d1['Open']) / d1['Open']
            is_long_d1 = rise_d1 >= 0.07  # 어제 7% 이상 장대양봉
            
            body_d0 = abs(d0['Close'] - d0['Open']) / d0['Open']
            is_doji_d0 = body_d0 <= 0.03  # 오늘 몸통 3% 이하 도지
            
            mid_d1 = (d1['Close'] + d1['Open']) / 2
            is_hold_d0 = d0['Close'] >= mid_d1  # 어제 몸통의 절반(중심선) 위에서 가격 방어
            
            if is_long_d1 and is_doji_d0 and is_hold_d0:
                result["sandwich"] = {
                    "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                    "패턴": "🥪 샌드위치 대기 (매복)",
                    "상승률": f"어제 +{round(rise_d1*100, 1)}% / 오늘 도지",
                    "발견시간": time.strftime("%H:%M:%S")
                }
        except: pass

        # === 급등 대기 (눌림목) 로직 ===
        try:
            d0, d1, d2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
            if d1['Open'] > 0 and d2['Volume'] > 0:
                if (((d1['Close'] - d1['Open']) / d1['Open'] >= 0.06) and 
                    (d1['Volume'] >= d2['Volume'] * 2.0) and 
                    (d0['Close'] < d1['Close']) and 
                    (d0['Volume'] <= d1['Volume'] * 0.40)):
                    result["surge_prep"] = {
                        "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                        "패턴": "🚀 급등 대기 (눌림목)",
                        "조건": f"전일 {round(((d1['Close']-d1['Open'])/d1['Open'])*100,1)}%↑ 대량거래 / 금일 거래급감",
                        "발견시간": time.strftime("%H:%M:%S")
                    }
        except: pass

        for i in range(3):
            idx = -1 - i
            if abs(idx) > len(df): break
            curr, prev = df.iloc[idx], df.iloc[idx-1]
            
            if pd.isna(curr['EMA60']): continue
            
            is_cross = (prev['EMA5'] <= prev['EMA20']) and (curr['EMA5'] > curr['EMA20'])
            is_trend = curr['EMA20'] > curr['EMA60']
            is_super_up = curr.get('stDir') == 1
            is_danger = ((curr['Close'] - curr['Open']) > (curr['Open'] * 0.10)) or (curr['RSI'] > 75) or (((curr['Close'] - curr['EMA20']) / curr['EMA20']) > 0.20)

            sig_sniper = is_cross and is_trend and is_super_up and not is_danger
            sig_normal = is_cross and (not sig_sniper) and (not is_danger)

            when_txt = f"{i}봉 전" if timeframe == "4H" else {0: "오늘", 1: "1일 전", 2: "2일 전"}.get(i, f"{i}일 전")

            touch_lines = []
            if 0 <= (curr['Close'] - curr['EMA20']) / curr['EMA20'] <= 0.02: touch_lines.append("20선")
            if 0 <= (curr['Close'] - curr['EMA60']) / curr['EMA60'] <= 0.02: touch_lines.append("60선")
            if not pd.isna(curr['EMA200']) and 0 <= (curr['Close'] - curr['EMA200']) / curr['EMA200'] <= 0.02: touch_lines.append("200선")

            if sig_sniper and result['sniper'] is None:
                result["sniper"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "RSI": round(curr['RSI'], 1), "신호": f"🎯 스나이퍼 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}
            if sig_normal and result['entry'] is None:
                result["entry"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "RSI": round(curr['RSI'], 1), "신호": f"✅ 추세 진입 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}
            if touch_lines and result['touch'] is None:
                result["touch"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "RSI": round(curr['RSI'], 1), "터치 라인": f"🧲 {', '.join(touch_lines)} 지지 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}

        return result
    except Exception as e:
        return result

# ==========================================
# 5. UI 및 멀티스레드 실행
# ==========================================
with st.sidebar:
    st.header("⚙️ 헌터 설정")
    market = st.selectbox("사냥터 선택", ["KOSPI (코스피)", "KOSDAQ (코스닥)", "NASDAQ (나스닥 전체)", "S&P 500 (미국 우량주)", "Russell 2000 (러셀 2000/NYSE)"])
    limit_option = st.select_slider("검색 범위 (시가총액 상위 N개)", options=["50", "100", "300", "500", "1000", "2000", "전체 (All)"], value="500")
    st.divider()
    auto_loop = st.checkbox("🔁 무한 자동 반복", value=False)
    interval = st.number_input("대기 시간 (분)", min_value=1, value=10)
    
    if HAS_WINSOUND:
        sound_on = st.checkbox("🔊 알람 켜기 (PC전용)", value=True)
    else:
        st.caption("📱 알람 기능은 모바일/웹 환경에서 지원되지 않습니다.")
        sound_on = False
        
    show_log = st.checkbox("📝 분석 로그 보기", value=True)
    
    if st.button("↻ 데이터 초기화"):
        st.cache_data.clear()
        st.rerun()
        
    run_btn = st.button("🚀 사냥 시작", type="primary")
    stop_btn = st.button("🛑 중지")

if 'running' not in st.session_state: st.session_state.running = False
if run_btn: st.session_state.running = True
if stop_btn:
    st.session_state.running = False
    st.warning("스캔이 중지되었습니다.")

def process_stock_wrapper(stock):
    return stock, analyze_stock(stock, "1D"), analyze_stock(stock, "4H")

if st.session_state.running:
    placeholder = st.empty()
    while st.session_state.running:
        with placeholder.container():
            target_list = get_stock_list_final(market, limit_option)
            st.info(f"🔍 [{time.strftime('%H:%M:%S')}] '{market}' 고속 스캔 시작... (대상: {len(target_list)}개)")
            if not target_list:
                st.error("종목 리스트를 불러오지 못했습니다.")
                st.session_state.running = False
                break
                
            d_sniper, d_entry, d_touch, d_surge, d_sandwich = [], [], [], [], []
            h_sniper, h_entry, h_touch, h_surge, h_sandwich = [], [], [], [], []
            
            bar, status_text, log_box = st.progress(0), st.empty(), st.empty()
            total, success_cnt = len(target_list), 0
            
            main_tab1, main_tab2 = st.tabs(["📅 일봉 (Daily)", "⏳ 4시간봉 (4-Hour)"])
            with main_tab1:
                t1_a, t1_b, t1_c, t1_d, t1_e = st.tabs(["🎯 스나이퍼", "✅ 추세 진입", "🧲 지지선 터치", "🚀 급등 대기", "🥪 샌드위치 대기"])
                d_table_sniper, d_table_entry, d_table_touch, d_table_surge, d_table_sandwich = t1_a.empty(), t1_b.empty(), t1_c.empty(), t1_d.empty(), t1_e.empty()
                
            with main_tab2:
                t2_a, t2_b, t2_c, t2_d, t2_e = st.tabs(["🎯 스나이퍼", "✅ 추세 진입", "🧲 지지선 터치", "🚀 급등 대기", "🥪 샌드위치 대기"])
                h_table_sniper, h_table_entry, h_table_touch, h_table_surge, h_table_sandwich = t2_a.empty(), t2_b.empty(), t2_c.empty(), t2_d.empty(), t2_e.empty()

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(process_stock_wrapper, stock): stock for stock in target_list}
                for i, future in enumerate(as_completed(futures)):
                    if not st.session_state.running:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    if i % 5 == 0: bar.progress((i + 1) / total)
                    stock_name = futures[future]['name']
                    if show_log: status_text.text(f"Scanning... {stock_name} ({i+1}/{total})")
                    log_box.caption(f"발견된 종목: {success_cnt}개 (1D & 4H 통합)")
                    
                    try:
                        stock, res_d, res_h = future.result()
                        found = False
                        
                        if res_d['sniper']: d_sniper.append(res_d['sniper']); found=True
                        if res_d['entry']: d_entry.append(res_d['entry']); found=True
                        if res_d['touch']: d_touch.append(res_d['touch']); found=True
                        if res_d['surge_prep']: d_surge.append(res_d['surge_prep']); found=True
                        if res_d['sandwich']: d_sandwich.append(res_d['sandwich']); found=True
                        
                        if res_h['sniper']: h_sniper.append(res_h['sniper']); found=True
                        if res_h['entry']: h_entry.append(res_h['entry']); found=True
                        if res_h['touch']: h_touch.append(res_h['touch']); found=True
                        if res_h['surge_prep']: h_surge.append(res_h['surge_prep']); found=True
                        if res_h['sandwich']: h_sandwich.append(res_h['sandwich']); found=True
                        
                        if found:
                            success_cnt += 1
                            if sound_on and HAS_WINSOUND: 
                                try: winsound.Beep(1000, 150)
                                except: pass
                            st.toast(f"발견! {stock['name']}", icon="🚨")
                            
                        if d_sniper: d_table_sniper.dataframe(pd.DataFrame(d_sniper), use_container_width=True)
                        if d_entry: d_table_entry.dataframe(pd.DataFrame(d_entry), use_container_width=True)
                        if d_touch: d_table_touch.dataframe(pd.DataFrame(d_touch), use_container_width=True)
                        if d_surge: d_table_surge.dataframe(pd.DataFrame(d_surge), use_container_width=True)
                        if d_sandwich: d_table_sandwich.dataframe(pd.DataFrame(d_sandwich), use_container_width=True)
                        
                        if h_sniper: h_table_sniper.dataframe(pd.DataFrame(h_sniper), use_container_width=True)
                        if h_entry: h_table_entry.dataframe(pd.DataFrame(h_entry), use_container_width=True)
                        if h_touch: h_table_touch.dataframe(pd.DataFrame(h_touch), use_container_width=True)
                        if h_surge: h_table_surge.dataframe(pd.DataFrame(h_surge), use_container_width=True)
                        if h_sandwich: h_table_sandwich.dataframe(pd.DataFrame(h_sandwich), use_container_width=True)
                            
                    except Exception:
                        continue
                        
            bar.progress(100)
            status_text.text("스캔 완료!")
            log_box.empty()
            
            if not (d_sniper or d_entry or d_touch or d_surge or d_sandwich or h_sniper or h_entry or h_touch or h_surge or h_sandwich):
                st.warning("조건에 맞는 종목을 찾지 못했습니다.")
                
            if auto_loop:
                for s in range(interval * 60, 0, -1):
                    if not st.session_state.running: break
                    st.caption(f"다음 스캔까지 {s}초 대기 중...")
                    time.sleep(1)
                if st.session_state.running:
                    placeholder.empty()
                    st.rerun()
            else:
                st.session_state.running = False
                break
