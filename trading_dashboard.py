import streamlit as st

import ccxt

import pandas as pd

import plotly.graph_objects as go

from plotly.subplots import make_subplots

import yfinance as yf

import requests

import os



# --- 1. 页面配置与 CSS 美化 ---

st.set_page_config(page_title="Alpha交易员战情室", layout="wide", page_icon="📈")



# 现代仪表盘风格 CSS

st.markdown("""

<style>

    .stApp {background-color: #f8f9fa;}

    header {visibility: hidden;}

    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}

    

    /* 指标卡片 */

    div[data-testid="stMetric"] {

        background-color: #ffffff;

        border-radius: 16px;

        padding: 15px 20px;

        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);

        border: 1px solid #f1f3f5;

        transition: transform 0.2s;

    }

    div[data-testid="stMetric"]:hover {

        transform: translateY(-2px);

        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);

    }

    div[data-testid="stMetricLabel"] {color: #868e96; font-size: 14px; font-weight: 500;}

    div[data-testid="stMetricValue"] {color: #212529; font-weight: 700; font-family: "SF Pro Display", sans-serif;}

    

    /* 标题渐变 */

    h1, h2, h3 {

        background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);

        -webkit-background-clip: text;

        -webkit-text-fill-color: transparent;

        font-weight: 800;

    }

</style>

""", unsafe_allow_html=True)



# --- 2. 核心数据获取函数 (前端实时获取盘口) ---

@st.cache_data(ttl=10) # 盘口数据缓存10秒

def get_live_data(symbol='BTC/USDT'):

    # ⚠️ 确保这里的端口和 collector.py 以及你的 VPN 保持一致

    PROXY_PORT = 17890 

    proxies = {

        'http': f'http://127.0.0.1:{PROXY_PORT}',

        'https': f'http://127.0.0.1:{PROXY_PORT}',

    }

    

    try:

        # 使用 OKX 获取实时盘口 (Binance 限制 IP)

        exchange = ccxt.okx({

            'proxies': proxies,

            'timeout': 10000, 

            'enableRateLimit': True

        })

        

        okx_symbol = f"{symbol}:USDT" if ':' not in symbol else symbol

        

        # 获取基础数据

        ticker = exchange.fetch_ticker(okx_symbol)

        funding = exchange.fetch_funding_rate(okx_symbol)

        oi_data = exchange.fetch_open_interest(okx_symbol)

        depth = exchange.fetch_order_book(okx_symbol, limit=20)

        

        return ticker['last'], funding['fundingRate'], oi_data['openInterestAmount'], depth, None



    except Exception as e:

        return 0, 0, 0, {}, str(e)



# 辅助数据获取

def get_fear_greed():

    try:

        r = requests.get("https://api.alternative.me/fng/").json()

        return int(r['data'][0]['value'])

    except:

        return 50



def get_mstr_data():

    try:

        mstr = yf.Ticker("MSTR")

        hist = mstr.history(period="1mo")

        if hist.empty: return 0, 0, 0

        return hist['Close'].iloc[-1], hist['Volume'].iloc[-1], hist['Volume'].mean()

    except:

        return 0, 0, 0



# 盘口分析逻辑

def analyze_orderbook(depth, current_price):

    if not depth or 'bids' not in depth or 'asks' not in depth:

        return 0, 0, "数据加载中", ""

        

    bids = depth['bids']

    asks = depth['asks']

    

    if len(bids) == 0 or len(asks) == 0:

        return 0, 0, "数据为空", ""



    limit = min(10, len(bids), len(asks))

    bid_vol_top = sum([item[1] for item in bids[:limit]])

    ask_vol_top = sum([item[1] for item in asks[:limit]])

    

    ratio = bid_vol_top / ask_vol_top if ask_vol_top > 0 else 1

    signal = "⚖️ 平衡"

    if ratio > 2: signal = "🟢 买盘强劲 (护盘)"

    if ratio < 0.5: signal = "🔴 卖压沉重 (压盘)"

    

    wall_alert = ""

    if len(bids) > 0 and bids[0][1] > 20: wall_alert += f"⚠️ 买一有大单 ({bids[0][1]}) "

    if len(asks) > 0 and asks[0][1] > 20: wall_alert += f"⚠️ 卖一有大单 ({asks[0][1]}) "

    

    return bid_vol_top, ask_vol_top, signal, wall_alert



# --- 3. 主界面布局 ---



# Sidebar

st.sidebar.header("控制台")

symbol_select = st.sidebar.selectbox("标的", ["BTC/USDT", "ETH/USDT"])

if st.sidebar.button("🔄 立即刷新界面"):

    st.rerun()



# 获取实时数据

with st.spinner('正在同步市场数据...'):

    price, funding_rate, oi, depth, error_msg = get_live_data(symbol_select)

    fg_index = get_fear_greed()

    mstr_price, mstr_vol, mstr_avg_vol = get_mstr_data()



if error_msg:

    st.error(f"连接失败，请检查 VPN 端口设置 (当前代码设为 17890)。\n报错: {error_msg}")



# === 第一部分：Top Banner 核心数据 ===

st.subheader("🔥 Market Overview")



col1, col2, col3, col4, col5 = st.columns(5)

with col1:

    st.metric(symbol_select, f"${price:,.2f}")

with col2:

    fr_pct = funding_rate * 100

    st.metric("资金费率", f"{fr_pct:.4f}%", delta="高费率预警" if fr_pct > 0.05 else None, delta_color="inverse")

with col3:

    st.metric("持仓量 (OI)", f"{oi:,.0f}")

with col4:

    st.metric("贪婪指数", f"{fg_index}")

with col5:

    vol_ratio = mstr_vol / mstr_avg_vol if mstr_avg_vol else 0

    st.metric("MSTR", f"${mstr_price:.0f}", f"Vol: {vol_ratio:.1f}x")



st.markdown("---")



# === 第二部分：盘口挂单分布 (Order Book) ===

# ⚠️ 这里是唯一的盘口展示区

st.header("📊 盘口挂单分布 (实时)")

bid_vol, ask_vol, ob_signal, wall_alert = analyze_orderbook(depth, price)



ob_c1, ob_c2 = st.columns([3, 1])



with ob_c1:

    if depth and 'bids' in depth:

        try:

            # 数据清洗与绘图

            bids_clean = [item[:2] for item in depth['bids']]

            asks_clean = [item[:2] for item in depth['asks']]

            bids_df = pd.DataFrame(bids_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            asks_df = pd.DataFrame(asks_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            bids_df['cumulative'] = bids_df['vol'].cumsum()

            asks_df['cumulative'] = asks_df['vol'].cumsum()

            

            fig = go.Figure()

            fig.add_trace(go.Scatter(x=bids_df['price'], y=bids_df['cumulative'], fill='tozeroy', name='买单', line=dict(color='#00c853'))) # 鲜绿

            fig.add_trace(go.Scatter(x=asks_df['price'], y=asks_df['cumulative'], fill='tozeroy', name='卖单', line=dict(color='#ff1744'))) # 鲜红

            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:

            st.warning(f"绘图暂不可用: {e}")

    else:

        st.info("等待盘口数据...")



with ob_c2:

    st.metric("买盘厚度 (Top10)", f"{bid_vol:.2f}")

    st.metric("卖盘厚度 (Top10)", f"{ask_vol:.2f}")

    st.markdown(f"**状态**: {ob_signal}")

    if wall_alert: st.error(wall_alert)



st.markdown("---")



# === 第三部分：核心指标趋势追踪 (读取后台CSV) ===

st.header("📈 历史趋势追踪 (每5分钟更新)")



csv_file = 'market_history.csv'



if os.path.exists(csv_file):

    try:

        # 1. 读取 CSV

        history_df = pd.read_csv(csv_file)

        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])

        history_df = history_df.sort_values('timestamp')

        

        if not history_df.empty:

            # 图表 A: 资金费率

            st.subheader("1. 资金费率历史走势")

            fig_fr = go.Figure()

            fig_fr.add_trace(go.Scatter(

                x=history_df['timestamp'], y=history_df['funding_rate'] * 100, 

                mode='lines', fill='tozeroy', name='费率 %',

                line=dict(color='#4facfe', width=3), fillcolor='rgba(79, 172, 254, 0.1)'

            ))

            fig_fr.add_hline(y=0.01, line_dash="dash", line_color="gray", annotation_text="基准")

            fig_fr.update_layout(height=300, margin=dict(t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

            st.plotly_chart(fig_fr, use_container_width=True)



            # 图表 B: 价格 vs OI

            st.subheader("2. 价格 vs 持仓量")

            fig_oi = make_subplots(specs=[[{"secondary_y": True}]])

            fig_oi.add_trace(go.Scatter(x=history_df['timestamp'], y=history_df['price'], name="价格", mode='lines', line=dict(color='#fa709a', width=3)), secondary_y=False)

            fig_oi.add_trace(go.Scatter(x=history_df['timestamp'], y=history_df['oi'], name="OI", mode='lines', line=dict(color='#667eea', width=2, dash='dot')), secondary_y=True)

            fig_oi.update_layout(height=350, margin=dict(t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")

            st.plotly_chart(fig_oi, use_container_width=True)

            

            st.caption(f"数据源: {csv_file} | 记录数: {len(history_df)}")

        else:

            st.info("CSV 文件为空，等待后台脚本写入数据...")

            

    except Exception as e:

        st.error(f"读取历史数据失败: {e}")

else:

    st.warning("⚠️ 未检测到历史数据文件。请确保已运行 'python collector.py' 启动后台采集。")
