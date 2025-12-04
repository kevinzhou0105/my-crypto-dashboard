import streamlit as st

import ccxt

import pandas as pd

import plotly.graph_objects as go

import yfinance as yf

import requests

from datetime import datetime, timedelta

import time



# --- 页面配置 ---

st.set_page_config(page_title="Alpha交易员战情室", layout="wide", page_icon="📈")

st.title("🔥 Alpha Trader 监控面板")

st.markdown("---")



# --- 1. 数据获取模块 (后端) ---



# --- 修改后的数据获取模块 ---



@st.cache_data(ttl=60)

def get_binance_data(symbol='BTC/USDT'):

    # 云端服务器在美国，不需要 proxies 参数

    try:

        # 纯净连接

        exchange = ccxt.binanceusdm({

            'timeout': 30000, 

            'enableRateLimit': True

        })

        

        ticker = exchange.fetch_ticker(symbol)

        price = ticker['last']

        

        funding = exchange.fetch_funding_rate(symbol)

        funding_rate = funding['fundingRate']

        

        oi_data = exchange.fetch_open_interest(symbol)

        open_interest = oi_data['openInterestAmount']

        

        depth = exchange.fetch_order_book(symbol, limit=20)

        

        return price, funding_rate, open_interest, depth, None 



    except Exception as e:

        return 0, 0, 0, {'bids': [], 'asks': []}, str(e)



def get_ls_ratio(symbol='BTCUSDT'):

    # Binance 公开接口获取多空比 (Top Traders)

    try:

        url = "https://fapi.binance.com/futures/data/topLongShortAccountRatio"

        params = {'symbol': symbol, 'period': '5m', 'limit': 1}

        r = requests.get(url, params=params).json()

        if r:

            return float(r[0]['longShortRatio'])

        return 0

    except:

        return 0



def get_fear_greed():

    try:

        r = requests.get("https://api.alternative.me/fng/").json()

        return int(r['data'][0]['value'])

    except:

        return 50



def get_mstr_data():

    try:

        # 获取 MSTR 数据

        mstr = yf.Ticker("MSTR")

        hist = mstr.history(period="1mo")

        if hist.empty:

            return 0, 0, 0

        

        last_vol = hist['Volume'].iloc[-1]

        avg_vol = hist['Volume'].mean()

        last_price = hist['Close'].iloc[-1]

        

        return last_price, last_vol, avg_vol

    except:

        return 0, 0, 0



# --- 2. 逻辑分析模块 (策略核心) ---



def analyze_funding(rate):

    """一、资金费率分析逻辑"""

    rate_pct = rate * 100

    color = "white"

    status = "无特殊信号"

    

    if rate_pct >= 0.10:

        status = "⚠️ 极端正费率 (牛市尾声/无脑减仓)"

        color = "red"

    elif 0.07 <= rate_pct < 0.10:

        status = "🚨 高烧预警 (只留底仓)"

        color = "orange"

    elif 0.03 <= rate_pct < 0.07:

        status = "👀 正常偏高 (不开新仓)"

        color = "yellow"

    elif 0 <= rate_pct < 0.03:

        status = "✅ 健康区间 (最舒服持仓)"

        color = "green"

    elif -0.04 <= rate_pct < 0:

        status = "💎 轻度负费率 (最佳加仓)"

        color = "cyan"

    elif rate_pct <= -0.05:

        status = "🚀 极端负费率 (无脑抄底)"

        color = "blue"

        

    return rate_pct, status, color



def analyze_ls_ratio(ratio):

    """三、多空持仓比分析逻辑"""

    status = "中性"

    color = "white"

    

    if ratio >= 3.0:

        status = "💥 必炸多头 (反手空)"

        color = "red"

    elif ratio >= 2.5:

        status = "🏃 准备跑路 (减仓70%)"

        color = "orange"

    elif ratio <= 0.4:

        status = "🚀 空头必炸 (满仓多)"

        color = "green"

    

    return ratio, status, color



def analyze_orderbook(depth, current_price):

    """四、盘口分析 (简化版)"""

    bids = depth['bids']

    asks = depth['asks']

    

    # 计算前10档的厚度

    bid_vol_top = sum([item[1] for item in bids[:10]])

    ask_vol_top = sum([item[1] for item in asks[:10]])

    

    ratio = bid_vol_top / ask_vol_top if ask_vol_top > 0 else 1

    

    signal = "平衡"

    if ratio > 2: signal = "🟢 下方买盘强 (可能有护盘)"

    if ratio < 0.5: signal = "🔴 上方压盘重"

    

    # 简单的"大单"检测 (假设 > 20 BTC 为大单)

    big_wall_check = ""

    if bids[0][1] > 20: big_wall_check += f"⚠️ 发现买一 {bids[0][0]} 处有大单 ({bids[0][1]} BTC) - 警惕假护盘"

    if asks[0][1] > 20: big_wall_check += f"⚠️ 发现卖一 {asks[0][0]} 处有大单 ({asks[0][1]} BTC) - 警惕假压盘"

    

    return bid_vol_top, ask_vol_top, signal, big_wall_check



# --- 3. 界面布局模块 ---



# Sidebar

st.sidebar.header("配置")

symbol_select = st.sidebar.selectbox("选择币种", ["BTC/USDT", "ETH/USDT"])

refresh = st.sidebar.button("刷新数据")



# Main Data Fetch

with st.spinner('正在连接交易所...'):

    price, funding_rate, oi, depth, error = get_binance_data(symbol_select)

    if error:

        st.error(f"⚠️ 数据获取错误: {error}")

    ls_ratio = get_ls_ratio(symbol_select.replace('/', ''))

    fg_index = get_fear_greed()

    mstr_price, mstr_vol, mstr_avg_vol = get_mstr_data()



# Layout

col1, col2, col3 = st.columns(3)



with col1:

    st.subheader(f"💰 {symbol_select} 价格")

    st.metric(label="Current Price", value=f"${price:,.2f}")



with col2:

    st.subheader("😨 贪婪恐惧指数")

    fg_color = "red" if fg_index > 80 else ("green" if fg_index < 20 else "gray")

    st.markdown(f"<h2 style='color:{fg_color}'>{fg_index}</h2>", unsafe_allow_html=True)

    if fg_index > 90: st.warning("⚔️ 绝地武士绿光剑 - 牛市尾声信号！")

    if fg_index < 10: st.success("📉 极度恐惧 - 闭眼定投区间")



with col3:

    st.subheader("📊 MSTR 监控")

    vol_ratio = mstr_vol / mstr_avg_vol if mstr_avg_vol else 0

    st.metric("MSTR Price", f"${mstr_price:.2f}")

    st.metric("Vol / Avg Vol", f"{vol_ratio:.1f}x")

    if vol_ratio > 3: st.error("🔥 MSTR 底部爆量 > 3倍 (抄底信号)")



st.markdown("---")



# --- 核心指标区域 ---



c1, c2 = st.columns(2)



# 1. 资金费率

with c1:

    st.header("1. 资金费率 (Funding Rate)")

    fr_val, fr_msg, fr_col = analyze_funding(funding_rate)

    st.metric("当前费率", f"{fr_val:.4f}%")

    st.markdown(f"<div style='background-color:rgba(100,100,100,0.2);padding:10px;border-left:5px solid {fr_col}'>{fr_msg}</div>", unsafe_allow_html=True)

    

    st.caption("逻辑: >0.1% 减仓 | < -0.05% 抄底")



# 2. 多空比与 OI

with c2:

    st.header("2. 情绪与持仓 (LS Ratio & OI)")

    

    ls_val, ls_msg, ls_col = analyze_ls_ratio(ls_ratio)

    st.metric("顶级账户多空比", f"{ls_val}")

    st.markdown(f"<div style='background-color:rgba(100,100,100,0.2);padding:10px;border-left:5px solid {ls_col}'>{ls_msg}</div>", unsafe_allow_html=True)

    

    st.markdown("---")

    st.metric("未平仓合约 (OI)", f"{oi:,.0f} {symbol_select.split('/')[0]}")

    st.info("💡 记得对比价格走势：价格新高+OI跌=跑路; 价格新高+OI高=趋势健康")



st.markdown("---")



# 3. 盘口分析

st.header("3. 盘口挂单分布 (Order Book)")

bid_vol, ask_vol, ob_signal, wall_alert = analyze_orderbook(depth, price)



ob_col1, ob_col2 = st.columns([3, 1])

with ob_col1:

    # 绘制简易深度图

    bids_df = pd.DataFrame(depth['bids'], columns=['price', 'vol']).sort_values('price')

    asks_df = pd.DataFrame(depth['asks'], columns=['price', 'vol']).sort_values('price')

    

    # 累计量

    bids_df['cumulative'] = bids_df['vol'].cumsum()

    asks_df['cumulative'] = asks_df['vol'].cumsum()

    

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=bids_df['price'], y=bids_df['cumulative'], fill='tozeroy', name='买单 (Bids)', line=dict(color='green')))

    fig.add_trace(go.Scatter(x=asks_df['price'], y=asks_df['cumulative'], fill='tozeroy', name='卖单 (Asks)', line=dict(color='red')))

    fig.update_layout(title="买卖盘深度对比 (Top 20档)", height=300, margin=dict(l=0, r=0, t=30, b=0))

    st.plotly_chart(fig, use_container_width=True)



with ob_col2:

    st.metric("前10档买盘量", f"{bid_vol:.2f}")

    st.metric("前10档卖盘量", f"{ask_vol:.2f}")

    st.write(f"**结论:** {ob_signal}")

    if wall_alert:

        st.warning(wall_alert)



st.markdown("---")



# 4. ETF 与 备忘录

st.header("4. 现货 ETF & 备忘")

st.info("⚠️ 注意：实时 ETF 流入数据通常需要付费 API (如 Glassnode/Coinglass)。此处建议手动关注每日美股收盘后数据。")



col_etf1, col_etf2 = st.columns(2)

with col_etf1:

    st.markdown("""

    **ETF 铁律:**

    * 单日净流入 > 5亿 USD → **加仓**

    * 单日净流入 > 10亿 USD + 负费率 → **满仓杠杆**

    * 流出中价格新高 → **假突破，清仓**

    """)

with col_etf2:

    st.markdown("""

    **OI 黄金法则 (自检):**

    1.  Price ⬆️ + OI ⬆️ = **趋势健康**

    2.  Price ⬆️ + OI ⬇️ = **主力跑路 (减仓)**

    3.  Price ⬇️ + OI ⬆️ = **V反预备 (关注)**

    4.  Price ➖ + OI ⬆️ = **主力建仓 (潜伏)**

    """)



st.caption("数据来源: Binance Futures (Price/OI/Funding), Yahoo Finance (MSTR), Alternative.me (F&G). 此面板仅供参考，不构成投资建议。")

