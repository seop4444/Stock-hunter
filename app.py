import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests
import re
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="Stock Hunter v28 (수급 탑재판)", layout="wide")
st.title(" 🎯 Stock Hunter v28 (실시간 수급/캐시 무력화 버전)")
st.markdown("""
### ⚡ 멀티 타임프레임 고속 스캔 & 세력 수급 추적
**업데이트:** 핵심 타점(샌드위치, 급등 대기, 스나이퍼, 추세 진입) 포착 시 네이버 증권에서 **당일 실시간 수급(개인/외국인/기관)** 데이터를 즉시 긁어와 세력의 '가짜 눌림목(설거지)'을 완벽하게 걸러냅니다.
""")

# ==========================================
# 1.5. 실시간 대시보드
# ==========================================
@st.cache_data(ttl=60)
def get_dashboard_data():
    oil_data = {"price": 0.0, "change": 0.0, "pct": 0.0, "history": None}
    kr_news, global_news = [], []
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
    except: pass

    def parse_pubdate(pubdate_str):
        try: return email.utils.parsedate_to_datetime(pubdate_str).strftime("%m-%d %H:%M")
        except: return ""

    try:
        kr_root = ET.fromstring(requests.get("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko").content)
        for item in kr_root.findall('.//item')[:4]: kr_news.append({"title": item.find('title').text, "date": parse_pubdate(item.find('pubDate').text)})
        us_root = ET.fromstring(requests.get("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en").content)
        for item in us_root.findall('.//item')[:4]: global_news.append({"title": item.find('title').text, "date": parse_pubdate(item.find('pubDate').text)})
    except:
        kr_news, global_news = [{"title": "뉴스 로딩 실패", "date": ""}], [{"title": "뉴스 로딩 실패", "date": ""}]

    return oil_data, kr_news, global_news

oil_data, kr_news, global_news = get_dashboard_data()

st.divider()
col1, col2, col3 = st.columns([1, 1.5, 1.5])
with col1:
    st.subheader("🛢️ WTI 원유 (Today)")
    if oil_data['price']: st.metric("Crude Oil", f"${oil_data['price']:.2f}", f"{oil_data['change']:.2f} ({oil_data['pct']:.2f}%)")
with col2:
    st.subheader("🇰🇷 국내 경제 뉴스")
    for n in kr_news: st.markdown(f"- **[{n['date']}]** {n['title']}" if n['date'] else f"- {n['title']}")
with col3:
    st.subheader("🌎 월스트리트 뉴스")
    for n in global_news: st.markdown(f"- **[{n['date']}]** {n['title']}" if n['date'] else f"- {n['title']}")
st.divider()

# ==========================================
# 2. 데이터 수집 (네이버 스텔스 크롤링 + 실시간 캐시 무력화)
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_list_final(market_name, scan_limit):
    results = []
    kr_garbage = ['KODEX', 'TIGER', 'ACE', 'KBSTAR', 'HANARO', 'SOL', 'KOSEF', 'ARIRANG', 'TIMEFOLIO', 'KOACT', 'WOORI', 'PLUS', 'MASTER', 'HK', 'FOCUS', 'RISE', 'KIWOOM', '1Q', 'WON', 'HERO', 'UNICORN', 'MIGHTY', 'QV', 'ETN', 'ETF', '스팩', 'SPAC', '인수목적', '전환', '선물', '채권', '레버리지', '인버스', '배당', '커버드콜', '리츠', 'REITS', '인프라', '선박', '투자', '펀드', '지주', '홀딩스']
    us_garbage = ['ETF', 'ETN', 'Acquisition', 'SPAC', 'Fund', 'Trust', 'REIT', 'Bull', 'Bear', '2X', '3X', 'Ultra', 'Short', 'ProShares', 'Direxion', 'Vanguard', 'iShares', 'Invesco', 'Global X', 'Schwab', 'First Trust']

    try:
        if "S&P" in market_name or "NASDAQ" in market_name or "Russell" in market_name:
            df = fdr.StockListing('S&P500') if "S&P" in market_name else (fdr.StockListing('NYSE') if "Russell" in market_name else fdr.StockListing('NASDAQ'))
            col_map = {c.lower(): c for c in df.columns}
            if 'marcap' in col_map: df = df.sort_values(by=col_map['marcap'], ascending=False)
            elif 'marketcap' in col_map: df = df.sort_values(by=col_map['marketcap'], ascending=False)
            if scan_limit != "전체 (All)": df = df.head(int(scan_limit))
            for idx, row in df.iterrows():
                ticker = str(row.get('Symbol', row.get('Code', '')))
                name = row.get('Name', ticker)
                if not any(kw.lower() in name.lower() for kw in us_garbage): results.append({"code": ticker, "name": name})
            return results
        else:
            sosok = "0" if "KOSPI" in market_name else "1"
            suffix = ".KS" if "KOSPI" in market_name else ".KQ"
            limit_val = 2000 if scan_limit == "전체 (All)" else int(scan_limit)
            max_pages = (limit_val // 50) + 2
            
            dummy_timestamp = int(time.time() * 1000)
            
            for page in range(1, max_pages):
                url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}&dummy={dummy_timestamp}"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
                res = requests.get(url, headers=headers)
                matches = re.findall(r'href="/item/main\.naver\?code=(\d+)".*?class="tltle">(.*?)</a>', res.text)
                if not matches: break
                for ticker, name in matches:
                    is_garbage = any(kw in name.upper() for kw in kr_garbage) or name.endswith('우') or name.endswith('우B') or '우(' in name
                    if not is_garbage: results.append({"code": ticker + suffix, "name": name})
                if len(results) >= limit_val: break
            return results
    except Exception as e:
        st.error(f"⚠️ 리스트 수집 오류: {str(e)}")
        return []

# ==========================================
# 2.5. 수급(개인/외국인/기관) 데이터 크롤링 엔진 (Pandas 파서 적용)
# ==========================================
def get_investor_trend(ticker):
    # 미국 주식은 수급 데이터 제공 불가
    if ".KS" not in ticker and ".KQ" not in ticker:
        return "-"
    try:
        clean_ticker = ticker.split('.')[0]
        url = f"https://finance.naver.com/item/frgn.naver?code={clean_ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        
        # 1. 데이터 요청 및 한글 인코딩 보호
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'euc-kr' 
        
        # 2. 낡은 정규식을 버리고, Pandas의 강력한 표(Table) 추출 기능 사용
        dfs = pd.read_html(io.StringIO(res.text))
        
        # 3. 여러 표 중에서 '기관'과 '외국인'이 적힌 진짜 수급 테이블만 타겟팅
        for df in dfs:
            cols_str = str(df.columns.tolist())
            if '기관' in cols_str and '외국인' in cols_str:
                df_clean = df.dropna(how='all')
                
                # 4. 가장 최신 날짜(오늘)의 데이터 추출
                for idx, row in df_clean.iterrows():
                    # 첫 열이 날짜 데이터(YYYY.MM.DD 형식)인지 확인
                    if str(row.iloc[0]).count('.') == 2: 
                        inst = str(row.iloc[5]).replace(',', '').replace('+', '')
                        frgn = str(row.iloc[6]).replace(',', '').replace('+', '')
                        
                        try:
                            inst_buy = int(float(inst))
                            foreign_buy = int(float(frgn))
                            # 주식은 제로섬 게임이므로 외인+기관의 반대 포지션이 개인
                            indiv_buy = -(inst_buy + foreign_buy) 
                        except:
                            return "장마감 집계중"
                            
                        def fmt(v):
                            if v > 0: return f"🔴+{v:,}"
                            elif v < 0: return f"🔵{v:,}"
                            return "0"
                            
                        return f"개인 {fmt(indiv_buy)} | 외인 {fmt(foreign_buy)} | 기관 {fmt(inst_buy)}"
                        
        return "데이터 없음"
    except Exception as e:
        return "수집 지연"

# ==========================================
# 3. 보조지표
# ==========================================
def calc_ema(series, span): return series.ewm(span=span, adjust=False).mean()
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - (100 / (1 + (gain / loss)))
def calc_supertrend(df, period=10, multiplier=3.0):
    hl2 = (df['High'] + df['Low']) / 2
    tr = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift()).abs(), (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    ub, lb = hl2 + (multiplier * atr), hl2 - (multiplier * atr)
    close_list, ub_list, lb_list, dir_list = df['Close'].tolist(), ub.tolist(), lb.tolist(), [1] * len(df)
    for i in range(1, len(df)):
        if pd.isna(close_list[i]) or pd.isna(ub_list[i-1]): continue
        if close_list[i] > ub_list[i-1]: dir_list[i] = 1
        elif close_list[i] < lb_list[i-1]: dir_list[i] = -1
        else:
            dir_list[i] = dir_list[i-1]
            if dir_list[i] == 1: lb_list[i] = max(lb_list[i], lb_list[i-1])
            else: ub_list[i] = min(ub_list[i], ub_list[i-1])
    return dir_list

# ==========================================
# 4. 분석 로직 (실시간 데이터 연동)
# ==========================================
def analyze_stock(ticker_info, timeframe):
    ticker, name = ticker_info['code'], ticker_info['name']
    result = {"sniper": None, "entry": None, "touch": None, "surge_prep": None, "sandwich": None, "reviews": []}
    
    # 💥 핵심 타점 발견 시에만 1회 호출하여 스캔 속도 저하 방지
    investor_data = None
    def get_inv():
        nonlocal investor_data
        if investor_data is None:
            investor_data = get_investor_trend(ticker)
        return investor_data
    
    try:
        if timeframe == "1D" and (".KS" in ticker or ".KQ" in ticker):
            clean_ticker = ticker.split('.')[0]
            df = fdr.DataReader(clean_ticker)
            if not df.empty:
                df = df.tail(250)
        else:
            tkr = yf.Ticker(ticker)
            df = tkr.history(period="1y", interval="1d") if timeframe == "1D" else tkr.history(period="60d", interval="1h")
            
        if df.empty or len(df) < 60: return result
        
        if isinstance(df.columns, pd.MultiIndex):
            try: df.columns = df.columns.get_level_values(0)
            except: pass

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        df = df[df.index.weekday < 5].dropna(subset=['Close', 'Open'])

        if timeframe == "4H":
            agg = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
            if 'Volume' not in df.columns: del agg['Volume']
            df = df.resample('4h').agg(agg).dropna()
            df = df[df.index.weekday < 5]

        df['EMA5'], df['EMA20'], df['EMA60'], df['EMA200'] = calc_ema(df['Close'], 5), calc_ema(df['Close'], 20), calc_ema(df['Close'], 60), calc_ema(df['Close'], 200)
        df['RSI'] = calc_rsi(df['Close'], 14)
        df['stDir'] = calc_supertrend(df, 10, 3.0)

        d0, d1, d2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
        d3 = df.iloc[-4] if len(df) >= 4 else None
        d4 = df.iloc[-5] if len(df) >= 5 else None

        # ==============================================
        # 📊 전일 타점 성적표 (수급 미포함)
        # ==============================================
        if d3 is not None:
            try:
                rise_d2 = (d2['Close'] - d2['Open']) / d2['Open']
                body_d1 = abs(d1['Close'] - d1['Open']) / d1['Open']
                support_line_review = d2['Open'] + ((d2['Close'] - d2['Open']) * 0.3)
                
                if rise_d2 >= 0.05 and body_d1 <= 0.04 and d1['Close'] >= support_line_review:
                    today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                    vol_pct = (d0['Volume'] - d1['Volume']) / d1['Volume'] * 100 if d1['Volume'] > 0 else 0
                    result["reviews"].append({
                        "종목명": name, "티커": ticker, "패턴": "🥪 샌드위치 (어제)",
                        "어제 종가": f"{round(d1['Close']):,}", "오늘 종가": f"{round(d0['Close']):,}",
                        "오늘 등락률": f"{'+' if today_pct > 0 else ''}{round(today_pct, 2)}%",
                        "오늘 거래량 증감": f"{'+' if vol_pct > 0 else ''}{round(vol_pct, 1)}%",
                        "발견시간": time.strftime("%H:%M:%S")
                    })
            except: pass

            try:
                if d2['Open'] > 0 and d3['Volume'] > 0:
                    if (((d2['Close'] - d2['Open']) / d2['Open'] >= 0.05) and 
                        (d2['Volume'] >= d3['Volume'] * 1.5) and 
                        (d1['Close'] <= d2['Close']) and 
                        (d1['Volume'] <= d2['Volume'] * 0.50)):
                        today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                        vol_pct = (d0['Volume'] - d1['Volume']) / d1['Volume'] * 100 if d1['Volume'] > 0 else 0
                        result["reviews"].append({
                            "종목명": name, "티커": ticker, "패턴": "🚀 급등 대기 (어제)",
                            "어제 종가": f"{round(d1['Close']):,}", "오늘 종가": f"{round(d0['Close']):,}",
                            "오늘 등락률": f"{'+' if today_pct > 0 else ''}{round(today_pct, 2)}%",
                            "오늘 거래량 증감": f"{'+' if vol_pct > 0 else ''}{round(vol_pct, 1)}%",
                            "발견시간": time.strftime("%H:%M:%S")
                        })
            except: pass

        # ==============================================
        # 🟢 현재 기준 사냥 로직 (수급 탑재)
        # ==============================================
        
        # === 🥪 샌드위치 (단봉 눌림) ===
        try:
            rise_d1 = (d1['Close'] - d1['Open']) / d1['Open']
            body_d0 = abs(d0['Close'] - d0['Open']) / d0['Open']
            support_line = d1['Open'] + ((d1['Close'] - d1['Open']) * 0.3)
            
            if rise_d1 >= 0.05 and body_d0 <= 0.04 and d0['Close'] >= support_line:
                yest_pct = (d1['Close'] - d2['Close']) / d2['Close'] * 100 if d2['Close'] else 0
                today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                vol_pct = (d0['Volume'] - d1['Volume']) / d1['Volume'] * 100 if d1['Volume'] > 0 else 0
                result["sandwich"] = {
                    "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                    "수급": get_inv(),
                    "패턴": "🥪 샌드위치 매복 (단봉)",
                    "등락률": f"어제 {'+' if yest_pct > 0 else ''}{round(yest_pct, 1)}% / 오늘 {'+' if today_pct > 0 else ''}{round(today_pct, 1)}%",
                    "거래량": f"어제 {int(d1['Volume']/10000)}만 / 오늘 {int(d0['Volume']/10000)}만 ({'+' if vol_pct > 0 else ''}{round(vol_pct, 1)}%)",
                    "발견시간": time.strftime("%H:%M:%S")
                }
        except: pass

        # === 🚀 급등 대기 (1일/2일/3일 눌림) ===
        try:
            # [1] 1일 눌림목
            if d1['Open'] > 0 and d2['Volume'] > 0:
                if (((d1['Close'] - d1['Open']) / d1['Open'] >= 0.05) and 
                    (d1['Volume'] >= d2['Volume'] * 1.5) and 
                    (d0['Close'] <= d1['Close'] * 1.02) and 
                    (d0['Close'] >= d1['Open'] + (d1['Close']-d1['Open'])*0.4) and 
                    (d0['Volume'] <= d1['Volume'] * 0.60)):
                    
                    yest_pct = (d1['Close'] - d2['Close']) / d2['Close'] * 100
                    today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                    vol_pct = (d0['Volume'] - d1['Volume']) / d1['Volume'] * 100
                    result["surge_prep"] = {
                        "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                        "수급": get_inv(),
                        "패턴": "🚀 급등 대기 (1일 눌림)",
                        "등락률": f"어제 {'+' if yest_pct > 0 else ''}{round(yest_pct, 1)}% / 오늘 {'+' if today_pct > 0 else ''}{round(today_pct, 1)}%",
                        "거래량": f"어제 {int(d1['Volume']/10000)}만 / 오늘 {int(d0['Volume']/10000)}만 ({round(vol_pct, 1)}%)",
                        "발견시간": time.strftime("%H:%M:%S")
                    }
                    
            # [2] 2일 연속 눌림목
            if result["surge_prep"] is None and d3 is not None and d2['Open'] > 0 and d3['Volume'] > 0:
                if (((d2['Close'] - d2['Open']) / d2['Open'] >= 0.05) and 
                    (d2['Volume'] >= d3['Volume'] * 1.5)):
                    mid_d2 = d2['Open'] + (d2['Close'] - d2['Open']) * 0.5
                    if (d1['Close'] >= mid_d2) and (d0['Close'] >= mid_d2) and (d0['Close'] <= d2['Close'] * 1.02):
                        if (d1['Volume'] <= d2['Volume'] * 0.7) and (d0['Volume'] <= d2['Volume'] * 0.5):
                            surge_pct = (d2['Close'] - d3['Close']) / d3['Close'] * 100
                            today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                            result["surge_prep"] = {
                                "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                                "수급": get_inv(),
                                "패턴": "🚀 급등 대기 (2일 눌림)",
                                "등락률": f"2일전 {'+' if surge_pct > 0 else ''}{round(surge_pct, 1)}% / 오늘 {'+' if today_pct > 0 else ''}{round(today_pct, 1)}%",
                                "거래량": f"급등일 {int(d2['Volume']/10000)}만 / 오늘 {int(d0['Volume']/10000)}만",
                                "발견시간": time.strftime("%H:%M:%S")
                            }

            # [3] 3일 연속 눌림목
            if result["surge_prep"] is None and d4 is not None and d3['Open'] > 0 and d4['Volume'] > 0:
                if (((d3['Close'] - d3['Open']) / d3['Open'] >= 0.05) and 
                    (d3['Volume'] >= d4['Volume'] * 1.5)):
                    mid_d3 = d3['Open'] + (d3['Close'] - d3['Open']) * 0.5
                    if (d2['Close'] >= mid_d3) and (d1['Close'] >= mid_d3) and (d0['Close'] >= mid_d3) and (d0['Close'] <= d3['Close'] * 1.02):
                        if (d0['Volume'] <= d3['Volume'] * 0.5):
                            surge_pct = (d3['Close'] - d4['Close']) / d4['Close'] * 100
                            today_pct = (d0['Close'] - d1['Close']) / d1['Close'] * 100
                            result["surge_prep"] = {
                                "종목명": name, "티커": ticker, "현재가": f"{round(d0['Close']):,}",
                                "수급": get_inv(),
                                "패턴": "🚀 급등 대기 (3일 눌림)",
                                "등락률": f"3일전 {'+' if surge_pct > 0 else ''}{round(surge_pct, 1)}% / 오늘 {'+' if today_pct > 0 else ''}{round(today_pct, 1)}%",
                                "거래량": f"급등일 {int(d3['Volume']/10000)}만 / 오늘 {int(d0['Volume']/10000)}만",
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

            when_txt = f"{i}봉 전" if timeframe == "4H" else {0: "오늘", 1: "1일 전", 2: "2일 전"}.get(i, f"{i}일 전")

            if is_cross and is_trend and is_super_up and not is_danger:
                if result['sniper'] is None: 
                    result["sniper"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "수급": get_inv(), "RSI": round(curr['RSI'], 1), "신호": f"🎯 스나이퍼 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}
            elif is_cross and not is_danger:
                if result['entry'] is None: 
                    result["entry"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "수급": get_inv(), "RSI": round(curr['RSI'], 1), "신호": f"✅ 추세 진입 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}
            
            t_lines = [line for diff, line in [((curr['Close']-curr['EMA20'])/curr['EMA20'], "20선"), ((curr['Close']-curr['EMA60'])/curr['EMA60'], "60선"), ((curr['Close']-curr['EMA200'])/curr['EMA200'], "200선") if not pd.isna(curr['EMA200']) else (-1, "")] if 0 <= diff <= 0.02]
            if t_lines and result['touch'] is None:
                # 💥 지지선 터치에는 수급을 추가하지 않음 (현섭님 요청 사항)
                result["touch"] = {"종목명": name, "티커": ticker, "현재가": f"{round(curr['Close']):,}", "RSI": round(curr['RSI'], 1), "터치 라인": f"🧲 {', '.join(t_lines)} 지지 ({when_txt})", "발견시간": time.strftime("%H:%M:%S")}

        return result
    except: return result

# ==========================================
# 5. UI 및 실행
# ==========================================
with st.sidebar:
    st.header("⚙️ 헌터 설정")
    market = st.selectbox("사냥터 선택", ["KOSPI (코스피)", "KOSDAQ (코스닥)", "NASDAQ (나스닥 전체)", "S&P 500 (미국 우량주)", "Russell 2000 (러셀 2000/NYSE)"])
    limit_option = st.select_slider("검색 범위 (시가총액 상위 N개)", options=["50", "100", "300", "500", "1000", "2000", "전체 (All)"], value="500")
    st.divider()
    auto_loop = st.checkbox("🔁 무한 자동 반복", value=False)
    interval = st.number_input("대기 시간 (분)", min_value=1, value=10)
    
    if HAS_WINSOUND: sound_on = st.checkbox("🔊 알람 켜기 (PC전용)", value=True)
    else: sound_on = False
        
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
    time.sleep(0.1)
    return stock, analyze_stock(stock, "1D"), analyze_stock(stock, "4H")

if st.session_state.running:
    placeholder = st.empty()
    while st.session_state.running:
        with placeholder.container():
            target_list = get_stock_list_final(market, limit_option)
            
            if not target_list:
                st.error("⚠️ 데이터를 불러올 수 없습니다.")
                st.session_state.running = False
                break
                
            st.info(f"🔍 [{time.strftime('%H:%M:%S')}] '{market}' 스캔 중...")
            
            d_sniper, d_entry, d_touch, d_surge, d_sandwich, d_review = [], [], [], [], [], []
            h_sniper, h_entry, h_touch, h_surge, h_sandwich, h_review = [], [], [], [], [], []
            
            bar, status_text = st.progress(0), st.empty()
            total = len(target_list)
            
            main_tab1, main_tab2 = st.tabs(["📅 일봉 (Daily)", "⏳ 4시간봉 (4-Hour)"])
            with main_tab1:
                t1_a, t1_b, t1_c, t1_d, t1_e, t1_f = st.tabs(["🎯 스나이퍼", "✅ 추세 진입", "🧲 지지선 터치", "🚀 급등 대기", "🥪 샌드위치 매복", "📊 전일 타점 성적표"])
                d_table_sniper, d_table_entry, d_table_touch, d_table_surge, d_table_sandwich, d_table_review = t1_a.empty(), t1_b.empty(), t1_c.empty(), t1_d.empty(), t1_e.empty(), t1_f.empty()
                
            with main_tab2:
                t2_a, t2_b, t2_c, t2_d, t2_e, t2_f = st.tabs(["🎯 스나이퍼", "✅ 추세 진입", "🧲 지지선 터치", "🚀 급등 대기", "🥪 샌드위치 매복", "📊 전일 타점 성적표"])
                h_table_sniper, h_table_entry, h_table_touch, h_table_surge, h_table_sandwich, h_table_review = t2_a.empty(), t2_b.empty(), t2_c.empty(), t2_d.empty(), t2_e.empty(), t2_f.empty()

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(process_stock_wrapper, stock): stock for stock in target_list}
                for i, future in enumerate(as_completed(futures)):
                    if not st.session_state.running:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    if i % 5 == 0: bar.progress((i + 1) / total)
                    if show_log: status_text.text(f"Scanning... {futures[future]['name']} ({i+1}/{total})")
                    
                    try:
                        stock, res_d, res_h = future.result()
                        found = False
                        
                        if res_d['sniper']: d_sniper.append(res_d['sniper']); found=True
                        if res_d['entry']: d_entry.append(res_d['entry']); found=True
                        if res_d['touch']: d_touch.append(res_d['touch']); found=True
                        if res_d['surge_prep']: d_surge.append(res_d['surge_prep']); found=True
                        if res_d['sandwich']: d_sandwich.append(res_d['sandwich']); found=True
                        if res_d['reviews']: d_review.extend(res_d['reviews']); found=True
                        
                        if res_h['sniper']: h_sniper.append(res_h['sniper']); found=True
                        if res_h['entry']: h_entry.append(res_h['entry']); found=True
                        if res_h['touch']: h_touch.append(res_h['touch']); found=True
                        if res_h['surge_prep']: h_surge.append(res_h['surge_prep']); found=True
                        if res_h['sandwich']: h_sandwich.append(res_h['sandwich']); found=True
                        if res_h['reviews']: h_review.extend(res_h['reviews']); found=True
                        
                        if found and sound_on and HAS_WINSOUND: 
                            try: winsound.Beep(1000, 150)
                            except: pass
                            
                        if d_sniper: d_table_sniper.dataframe(pd.DataFrame(d_sniper), use_container_width=True)
                        if d_entry: d_table_entry.dataframe(pd.DataFrame(d_entry), use_container_width=True)
                        if d_touch: d_table_touch.dataframe(pd.DataFrame(d_touch), use_container_width=True)
                        if d_surge: d_table_surge.dataframe(pd.DataFrame(d_surge), use_container_width=True)
                        if d_sandwich: d_table_sandwich.dataframe(pd.DataFrame(d_sandwich), use_container_width=True)
                        if d_review: d_table_review.dataframe(pd.DataFrame(d_review), use_container_width=True)
                        
                        if h_sniper: h_table_sniper.dataframe(pd.DataFrame(h_sniper), use_container_width=True)
                        if h_entry: h_table_entry.dataframe(pd.DataFrame(h_entry), use_container_width=True)
                        if h_touch: h_table_touch.dataframe(pd.DataFrame(h_touch), use_container_width=True)
                        if h_surge: h_table_surge.dataframe(pd.DataFrame(h_surge), use_container_width=True)
                        if h_sandwich: h_table_sandwich.dataframe(pd.DataFrame(h_sandwich), use_container_width=True)
                        if h_review: h_table_review.dataframe(pd.DataFrame(h_review), use_container_width=True)
                            
                    except: continue
                        
            bar.progress(100)
            status_text.text("스캔 완료!")

            if auto_loop:
                for s in range(interval * 60, 0, -1):
                    if not st.session_state.running: break
                    time.sleep(1)
                if st.session_state.running:
                    placeholder.empty()
                    st.rerun()
            else:
                st.session_state.running = False
                break
