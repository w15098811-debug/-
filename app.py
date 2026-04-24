import streamlit as st
import pandas as pd
import json
import os
import requests

st.set_page_config(page_title="ML 选品决策大脑", layout="wide", page_icon="🧠")
st.title("🧠 ML 跨境选品决策大脑 (终极完全体版)")

# ==========================================
# 🌐 0. 自动获取实时汇率 (带缓存机制)
# ==========================================
@st.cache_data(ttl=3600) # 缓存1小时，保证网页不卡顿
def get_realtime_exchange_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/MXN"
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data['rates']['CNY'])
    except:
        return 0.360 # 断网保底汇率

current_realtime_rate = get_realtime_exchange_rate()

# ==========================================
# 📁 1. 双轨制载入数据源
# ==========================================
st.sidebar.header("📁 1. 载入数据源")
uploaded_file = st.sidebar.file_uploader("上传最新 data.json (将覆盖默认数据)", type=['json'])

raw_data = None
if uploaded_file is not None:
    raw_data = json.load(uploaded_file)
    st.sidebar.success("✅ 已加载你刚上传的最新数据！")
elif os.path.exists("data.json"):
    with open("data.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    st.sidebar.info("📌 已自动加载云端默认的 data.json")

# ==========================================
# ⚙️ 核心参数面板
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. 商业核算参数")
ml_fee = st.sidebar.slider("平台抽成+税费 (%)", 10, 30, 17) / 100
shipping_cost = st.sidebar.number_input("单件国际+尾程运费 (比索)", value=75.0)

st.sidebar.markdown("---")
st.sidebar.header("💱 3. 汇率设置")
exchange_rate = st.sidebar.number_input(
    "当前汇率 (1 比索 = ? 人民币)", 
    value=current_realtime_rate, 
    format="%.4f", 
    help="🤖 已自动获取国际外汇市场最新汇率，你也可以手动微调"
)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ 4. 基础过滤漏斗")
col_a, col_b = st.sidebar.columns(2)
min_price = col_a.number_input("最低售价 (比索)", value=100)
max_price = col_b.number_input("最高售价 (比索)", value=5000)

target_margin = st.sidebar.slider("你的目标净利率 (%)", 5, 50, 15) / 100
min_reviews = st.sidebar.number_input("最低评价数", value=10)
only_full = st.sidebar.checkbox("只看 Full 仓竞品", value=False)

# ==========================================
# 🧠 数据处理与看板展示
# ==========================================
if raw_data is not None:
    df = pd.DataFrame(raw_data)
    
    # 🚀 核心清洗逻辑 —— 去除套娃重复商品
    if not df.empty and all(col in df.columns for col in ['title', 'price', 'image']):
        df = df.drop_duplicates(subset=['title', 'price', 'image'], keep='first')
    
    if 'price' in df.columns:
        df = df[(df['price'] >= min_price) & (df['price'] <= max_price)].copy()
        
        if not df.empty:
            df['预估单件净利'] = df['price'] * target_margin
            df['进货底线价'] = df['price'] - (df['price'] * ml_fee) - shipping_cost - df['预估单件净利']
            
            df['售价(RMB)'] = df['price'] * exchange_rate
            df['进货底线价(RMB)'] = df['进货底线价'] * exchange_rate
            
            df['当前设置下ROI'] = df.apply(
                lambda row: (row['预估单件净利'] / (row['进货底线价'] + shipping_cost)) if (row['进货底线价'] + shipping_cost) > 0 else -1, 
                axis=1
            )
            
            if 'reviews' in df.columns:
                df['预估历史总产值'] = df['price'] * df['reviews']
            
            if 'reviews' in df.columns:
                df = df[df['reviews'] >= min_reviews]
            if only_full and 'shipping' in df.columns:
                df = df[df['shipping'] == "Full (官方仓)"]
            
            recommended_df = df.copy()
            profitable_count = len(recommended_df[recommended_df['进货底线价'] > 0])

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📦 清洗后样本量", len(df))
            col2.metric("👁️ 展出竞品总数", len(recommended_df))
            
            if profitable_count > 0:
                col3.metric("🟢 利润达标款 (底线价>0)", profitable_count)
            else:
                col3.metric("🔴 利润达标款 (全军覆没)", "0", delta="-严重内卷", delta_color="inverse")
                
            if not recommended_df.empty:
                col4.metric("💰 展出品均价", f"${recommended_df['price'].mean():.2f}")

            st.markdown("---")
            st.subheader("📋 市场全量清单 (按进货空间从高到低排序)")
            
            recommended_df['1688链接'] = "https://www.1688.com/"
            recommended_df = recommended_df.sort_values(by='进货底线价', ascending=False)
            
            display_cols = ['image', 'title', 'price', '售价(RMB)']
            if 'reviews' in recommended_df.columns: display_cols.append('reviews')
            display_cols.extend(['进货底线价', '进货底线价(RMB)', '当前设置下ROI', '1688链接'])

            st.dataframe(
                recommended_df[display_cols],
                column_config={
                    "image": st.column_config.ImageColumn("📸 主图"),
                    "title": "西班牙语标题",
                    "price": st.column_config.NumberColumn("竞品售价 (比索)", format="$%.2f"),
                    "售价(RMB)": st.column_config.NumberColumn("售价 (人民币)", format="¥%.2f"),
                    "reviews": st.column_config.NumberColumn("评价数 (热度)"),
                    "进货底线价": st.column_config.NumberColumn("⚠️ 底线价 (比索)", format="$%.2f"),
                    "进货底线价(RMB)": st.column_config.NumberColumn("🇨🇳 1688底线价 (人民币)", format="¥%.4f"),
                    "当前设置下ROI": st.column_config.NumberColumn("🚀 预估 ROI", format="%.0f%%"),
                    "1688链接": st.column_config.LinkColumn("🛒 去核价", display_text="图搜1688")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.error("❌ 该价格区间内没有商品，请放宽左侧的售价范围。")
    else:
        st.warning("抓取的数据格式有误，没有找到价格信息。")
else:
    st.info("👈 正在等待数据... 请在左侧上传，或确保 GitHub 仓库中存在 data.json 文件。")