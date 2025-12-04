import streamlit as st

import ccxt

import os

import pandas as pd

import plotly.graph_objects as go

from plotly.subplots import make_subplots

import yfinance as yf

import requests

from datetime import datetime, timedelta

import time



# --- 页面配置 ---

st.set_page_config(page_title="Alpha交易员战情室", layout="wide", page_icon="📈")

# --- 🎨 界面美化：现代仪表盘风格 (Modern SaaS) ---

st.markdown("""

<style>

    /* 1. 全局背景：浅灰白，护眼且干净 */

    .stApp {

        background-color: #f8f9fa;

    }

    

    /* 2. 顶部 Banner：隐藏默认红线，调整Padding */

    header {visibility: hidden;}

    .main .block-container {

        padding-top: 2rem;

        padding-bottom: 2rem;

    }

    /* 3. 指标卡片 (Metrics)：悬浮圆角卡片效果 */

    div[data-testid="stMetric"] {

        background-color: #ffffff;

        border-radius: 16px;

        padding: 20px 24px;

        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* 柔和阴影 */

        border: 1px solid #f1f3f5;

        transition: transform 0.2s;

    }

    div[data-testid="stMetric"]:hover {

        transform: translateY(-2px); /* 鼠标悬停轻微上浮 */

        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);

    }

    /* 4. 指标文字优化 */

    div[data-testid="stMetricLabel"] {

        font-size: 14px;

        color: #868e96; /* 浅灰标签 */

        font-weight: 500;

    }

    div[data-testid="stMetricValue"] {

        font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif;

        font-weight: 700;

        color: #212529; /* 深黑数字 */

    }

    /* 5. 提示框 (Info/Warning) 样式优化 */

    div[data-testid="stAlert"] {

        border-radius: 12px;

        border: none;

        box-shadow: 0 2px 8px rgba(0,0,0,0.05);

    }

    

    /* 6. 标题渐变色 (品牌感) */

    h1 {

        background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);

        -webkit-background-clip: text;

        -webkit-text-fill-color: transparent;

        font-weight: 800;

    }

</style>

""", unsafe_allow_html=True)

st.title("🔥 Alpha Trader 监控面板")

st.markdown("---")



# --- 1. 数据获取模块 (后端) ---



# --- 修改后的数据获取模块 ---



# --- 替换整个数据获取模块 (改为 OKX 源) ---



@st.cache_data(ttl=60)

def get_binance_data(symbol='BTC/USDT'):

    # 强制将 symbol 转换为 OKX 的永续合约格式

    # 例如: BTC/USDT -> BTC/USDT:USDT

    if ':' not in symbol:

        okx_symbol = f"{symbol}:USDT"

    else:

        okx_symbol = symbol



    try:

        # 1. 尝试连接 OKX

        # OKX 相比 Binance 对云服务器 IP 更友好

        exchange = ccxt.okx({

            'timeout': 10000, 

            'enableRateLimit': True

        })

        

        # 获取数据

        ticker = exchange.fetch_ticker(okx_symbol)

        price = ticker['last']

        

        funding = exchange.fetch_funding_rate(okx_symbol)

        funding_rate = funding['fundingRate']

        

        oi_data = exchange.fetch_open_interest(okx_symbol)

        open_interest = oi_data['openInterestAmount']

        

        # OKX 的 orderbook 获取

        depth = exchange.fetch_order_book(okx_symbol, limit=20)

        

        return price, funding_rate, open_interest, depth, None



    except Exception as e:

        # 如果 OKX 也报错，说明云服务器被所有头部交易所拉黑了

        error_msg = (

            f"❌ 数据获取失败。\n"

            f"原因: 您的云服务器 IP (美国) 可能被交易所屏蔽。\n"

            f"建议: 请回到本地电脑运行此程序 (记得开启 VPN 代理)。\n"

            f"底层报错: {str(e)}"

        )

        return 0, 0, 0, {'bids': [], 'asks': []}, error_msg



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



# --- 历史数据管理模块 ---






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

    """四、盘口分析 (修复版 - 增加空数据保护)"""

    # 1. 安全检查：如果数据为空，直接返回默认值

    if not depth or 'bids' not in depth or 'asks' not in depth:

        return 0, 0, "数据暂不可用", ""

        

    bids = depth['bids']

    asks = depth['asks']

    

    # 2. 二次检查：确保列表里至少有数据

    if len(bids) == 0 or len(asks) == 0:

        return 0, 0, "盘口数据为空 (可能API受限)", ""



    # 计算前10档的厚度 (防止不足10档时报错)

    limit = min(10, len(bids), len(asks))

    bid_vol_top = sum([item[1] for item in bids[:limit]])

    ask_vol_top = sum([item[1] for item in asks[:limit]])

    

    ratio = bid_vol_top / ask_vol_top if ask_vol_top > 0 else 1

    

    signal = "平衡"

    if ratio > 2: signal = "🟢 下方买盘强 (可能有护盘)"

    if ratio < 0.5: signal = "🔴 上方压盘重"

    

    # 大单检测

    big_wall_check = ""

    # 确保有数据才去读第0个元素

    if len(bids) > 0 and bids[0][1] > 20: 

        big_wall_check += f"⚠️ 发现买一 {bids[0][0]} 处有大单 ({bids[0][1]}) "

    if len(asks) > 0 and asks[0][1] > 20: 

        big_wall_check += f"⚠️ 发现卖一 {asks[0][0]} 处有大单 ({asks[0][1]}) "

    

    return bid_vol_top, ask_vol_top, signal, big_wall_check



# --- 3. 界面布局模块 ---



# --- 界面布局模块 (新版：精简布局) ---



# Sidebar

st.sidebar.header("配置")

symbol_select = st.sidebar.selectbox("选择币种", ["BTC/USDT", "ETH/USDT"])

refresh = st.sidebar.button("刷新数据")



# Main Data Fetch

with st.spinner('正在连接交易所...'):

    # 获取数据 (注意：这里我们假设你已经用了之前给的 OKX 或者 修复版的 get_binance_data)

    price, funding_rate, oi, depth, error_msg = get_binance_data(symbol_select)

    

    if error_msg:

        st.error(f"⚠️ 数据获取失败: {error_msg}")

        ls_ratio = 0

        fg_index = 50

        mstr_price, mstr_vol, mstr_avg_vol = 0, 0, 0

    else:

        ls_ratio = get_ls_ratio(symbol_select.replace('/', ''))

        fg_index = get_fear_greed()

        mstr_price, mstr_vol, mstr_avg_vol = get_mstr_data()



# --- 1. 顶部核心数据栏 (Top Banner) ---

# 我们把原本散落在下面的 费率 和 OI 提到最上面，做成 5 列布局

st.subheader("🔥 Market Overview")



# 定义 5 列

top_c1, top_c2, top_c3, top_c4, top_c5 = st.columns(5)



with top_c1:

    st.metric(f"💰 {symbol_select}", f"${price:,.2f}")



with top_c2:

    # 资金费率 (带颜色逻辑)

    fr_pct = funding_rate * 100

    fr_color = "normal"

    if fr_pct > 0.05: fr_color = "off" # 红色警戒

    st.metric("资金费率", f"{fr_pct:.4f}%")



with top_c3:

    # OI (持仓量)

    st.metric("持仓量 (OI)", f"{oi:,.0f}")



with top_c4:

    # 贪婪指数

    fg_color = "red" if fg_index > 80 else ("green" if fg_index < 20 else "gray")

    st.metric("贪婪指数", f"{fg_index}", "F&G Index")



with top_c5:

    # MSTR

    vol_ratio = mstr_vol / mstr_avg_vol if mstr_avg_vol else 0

    st.metric("MSTR股价", f"${mstr_price:.0f}", f"Vol: {vol_ratio:.1f}x")



st.markdown("---")



# --- 2. 盘口挂单分布 (原第3部分，现在提上来) ---

# 注意：原本的 "1.资金费率" 和 "2.情绪" 已经删除

st.header("📊 盘口挂单分布 (Order Book)")

bid_vol, ask_vol, ob_signal, wall_alert = analyze_orderbook(depth, price)



ob_col1, ob_col2 = st.columns([3, 1])



with ob_col1:

    # --- 盘口绘图代码 (保持你之前的修复版代码不变) ---

    if depth and 'bids' in depth and 'asks' in depth and len(depth['bids']) > 0 and len(depth['asks']) > 0:

        try:

            bids_clean = [item[:2] for item in depth['bids']]

            asks_clean = [item[:2] for item in depth['asks']]

            bids_df = pd.DataFrame(bids_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            asks_df = pd.DataFrame(asks_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            bids_df['cumulative'] = bids_df['vol'].cumsum()

            asks_df['cumulative'] = asks_df['vol'].cumsum()

            

            fig = go.Figure()

            fig.add_trace(go.Scatter(x=bids_df['price'], y=bids_df['cumulative'], fill='tozeroy', name='买单', line=dict(color='green')))

            fig.add_trace(go.Scatter(x=asks_df['price'], y=asks_df['cumulative'], fill='tozeroy', name='卖单', line=dict(color='red')))

            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:

            st.warning(f"绘图出错: {e}")

    else:

        st.info("⌛️ 盘口数据加载中...")



with ob_col2:

    st.metric("Top10 买盘", f"{bid_vol:.2f}")

    st.metric("Top10 卖盘", f"{ask_vol:.2f}")

    st.caption(f"状态: {ob_signal}")

    if wall_alert: st.error(wall_alert)



st.markdown("---")

st.header("📈 核心指标趋势追踪 (后台每5分钟记录)")

# --- 修改后的历史数据读取逻辑 ---

csv_file = 'market_history.csv'

if os.path.exists(csv_file):

    try:

        # 1. 读取 CSV

        history_df = pd.read_csv(csv_file)

        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])

        

        # 2. 排序并取最近数据 (防止图表过密)

        history_df = history_df.sort_values('timestamp')

        

        # 3. 绘图 (代码完全复用之前的现代风格代码)

        if not history_df.empty:

            

            # --- 图表 A: 资金费率 ---

            st.subheader("1. 资金费率历史走势")

            fig_fr = go.Figure()

            fig_fr.add_trace(go.Scatter(

                x=history_df['timestamp'], 

                y=history_df['funding_rate'] * 100, 

                mode='lines',

                fill='tozeroy',

                name='费率 %',

                line=dict(color='#4facfe', width=3),

                fillcolor='rgba(79, 172, 254, 0.1)'

            ))

            fig_fr.add_hline(y=0.01, line_dash="dash", line_color="#adb5bd", annotation_text="基准")

            fig_fr.add_hline(y=0.05, line_dash="dash", line_color="#ff6b6b", annotation_text="高费率")

            fig_fr.update_layout(

                height=300, 

                margin=dict(t=10, b=0, l=0, r=0),

                paper_bgcolor='rgba(0,0,0,0)',

                plot_bgcolor='rgba(0,0,0,0)',

                yaxis=dict(gridcolor='#f1f3f5'),

                xaxis=dict(gridcolor='#f1f3f5')

            )

            st.plotly_chart(fig_fr, use_container_width=True)

            # --- 图表 B: 价格 vs OI ---

            st.subheader("2. 价格 vs 持仓量 (Price & OI)")

            fig_oi = make_subplots(specs=[[{"secondary_y": True}]])

            

            fig_oi.add_trace(

                go.Scatter(x=history_df['timestamp'], y=history_df['price'], name="BTC价格", mode='lines', line=dict(color='#fa709a', width=3)),

                secondary_y=False,

            )

            fig_oi.add_trace(

                go.Scatter(x=history_df['timestamp'], y=history_df['oi'], name="持仓量(OI)", mode='lines', line=dict(color='#667eea', width=2, dash='dot')),

                secondary_y=True,

            )

            fig_oi.update_layout(

                height=350, 

                margin=dict(t=10, b=0, l=0, r=0),

                paper_bgcolor='rgba(0,0,0,0)',

                plot_bgcolor='rgba(0,0,0,0)',

                yaxis=dict(gridcolor='#f1f3f5', showgrid=True),

                hovermode="x unified"

            )

            fig_oi.update_yaxes(title_text="价格", secondary_y=False)

            fig_oi.update_yaxes(title_text="持仓量", secondary_y=True, showgrid=False)

            st.plotly_chart(fig_oi, use_container_width=True)

            

            st.caption(f"数据来源: {csv_file} | 最近更新: {history_df.iloc[-1]['timestamp']}")

            

    except Exception as e:

        st.error(f"读取历史数据出错: {e}")

else:

    st.info("👋 尚未发现历史数据文件。请先运行 'collector.py' 脚本开始采集。")

# 增加一个手动刷新按钮，方便你想看最新图表时点一下

if st.button('🔄 刷新图表'):

    st.rerun()



st.markdown("---")



# 3. 盘口分析

st.header("3. 盘口挂单分布 (Order Book)")

bid_vol, ask_vol, ob_signal, wall_alert = analyze_orderbook(depth, price)



ob_col1, ob_col2 = st.columns([3, 1])

with ob_col1:

    # --- 修复开始：兼容 OKX/Binance 格式差异 ---

    # 只有当 bids 和 asks 都有数据时，才进行绘图

    if depth and 'bids' in depth and 'asks' in depth and len(depth['bids']) > 0 and len(depth['asks']) > 0:

        try:

            # 1. 数据清洗：无论交易返回几列数据，我们只截取前两列 (Price, Vol)

            # 这样可以完美解决 OKX 返回3列导致报错的问题

            bids_clean = [item[:2] for item in depth['bids']]

            asks_clean = [item[:2] for item in depth['asks']]



            # 2. 安全创建 DataFrame

            bids_df = pd.DataFrame(bids_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            asks_df = pd.DataFrame(asks_clean, columns=['price', 'vol']).astype(float).sort_values('price')

            

            # 3. 计算累计量 (Cumulative)

            bids_df['cumulative'] = bids_df['vol'].cumsum()

            asks_df['cumulative'] = asks_df['vol'].cumsum()

            

            # 4. 绘图

            fig = go.Figure()

            # 买单区域 (绿色)

            fig.add_trace(go.Scatter(

                x=bids_df['price'], 

                y=bids_df['cumulative'], 

                fill='tozeroy', 

                name='买单 (Bids)', 

                line=dict(color='green')

            ))

            # 卖单区域 (红色)

            fig.add_trace(go.Scatter(

                x=asks_df['price'], 

                y=asks_df['cumulative'], 

                fill='tozeroy', 

                name='卖单 (Asks)', 

                line=dict(color='red')

            ))

            

            fig.update_layout(

                title="买卖盘深度对比 (Top 20档)", 

                height=300, 

                margin=dict(l=0, r=0, t=30, b=0),

                xaxis_title="价格",

                yaxis_title="累计数量"

            )

            st.plotly_chart(fig, use_container_width=True)

            

        except Exception as e:

            st.warning(f"绘图数据处理出错: {e}")

    else:

        # 如果数据为空，显示占位符

        st.info("⌛️ 盘口数据加载中，或交易所暂未返回深度数据...")



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

