import streamlit as st
import pandas as pd
import json
import urllib.parse

st.set_page_config(page_title="ML 选品决策大脑", layout="wide", page_icon="🧠")
st.title("🧠 ML 跨境选品决策大脑 (上帝视角全量版)")

# ==========================================
# 📁 1. 载入数据源
# ==========================================
st.sidebar.header("📁 1. 载入数据源")
uploaded_file = st.sidebar.file_uploader("请上传爬虫生成的 data.json 文件", type=['json'])

# ==========================================
# ⚙️ 核心参数面板
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. 商业核算参数")
ml_fee = st.sidebar.slider("平台抽成+税费 (%)", 10, 30, 17) / 100
shipping_cost = st.sidebar.number_input("单件国际+尾程运费 (比索)", value=75.0)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ 3. 基础过滤漏斗")

col_a, col_b = st.sidebar.columns(2)
min_price = col_a.number_input("最低售价", value=100)
max_price = col_b.number_input("最高售价", value=5000)

target_margin = st.sidebar.slider("你的目标净利率 (%)", 5, 50, 15) / 100
min_reviews = st.sidebar.number_input("最低评价数", value=10)
only_full = st.sidebar.checkbox("只看 Full 仓竞品", value=False)

# ==========================================
# 🧠 数据处理与看板展示
# ==========================================
if uploaded_file is not None:
    raw_data = json.load(uploaded_file)
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        
        if 'price' in df.columns:
            # 1. 价格区间过滤
            df = df[(df['price'] >= min_price) & (df['price'] <= max_price)].copy()
            
            if not df.empty:
                # 2. 财务核算
                df['预估单件净利'] = df['price'] * target_margin
                df['进货底线价'] = df['price'] - (df['price'] * ml_fee) - shipping_cost - df['预估单件净利']
                
                # 计算 ROI (加入防报错机制，防止除以0)
                df['当前设置下ROI'] = df.apply(
                    lambda row: (row['预估单件净利'] / (row['进货底线价'] + shipping_cost)) if (row['进货底线价'] + shipping_cost) > 0 else -1, 
                    axis=1
                )
                
                if 'reviews' in df.columns:
                    df['预估历史总产值'] = df['price'] * df['reviews']
                
                # 3. 基础条件过滤 (不再过滤负利润！)
                if 'reviews' in df.columns:
                    df = df[df['reviews'] >= min_reviews]
                if only_full and 'shipping' in df.columns:
                    df = df[df['shipping'] == "Full (官方仓)"]
                
                # 🚀 核心解封：只要符合基础条件，全部展示！
                recommended_df = df.copy()
                
                # 单独计算出真正有利润的商品数量，用于顶部展示
                profitable_count = len(recommended_df[recommended_df['进货底线价'] > 0])

                # --- 界面展示 ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📦 价格区间样本", len(df))
                col2.metric("👁️ 展出竞品总数", len(recommended_df))
                
                # 用颜色区分到底有没有好品
                if profitable_count > 0:
                    col3.metric("🟢 利润达标款 (底线价>0)", profitable_count)
                else:
                    col3.metric("🔴 利润达标款 (全军覆没)", "0", delta="-严重内卷", delta_color="inverse")
                    
                if not recommended_df.empty:
                    col4.metric("💰 展出品均价", f"${recommended_df['price'].mean():.2f}")

                st.markdown("---")

                if not recommended_df.empty:
                    st.subheader("📋 市场全量清单 (按进货空间从高到低排序)")
                    
                    # 生成 1688 图搜通用链接
                    recommended_df['1688链接'] = "https://www.1688.com/"
                    # 按进货底线价排序，把利润最高的排在最上面，亏本的最下面
                    recommended_df = recommended_df.sort_values(by='进货底线价', ascending=False)
                    
                    display_cols = ['image', 'title', 'price']
                    if 'reviews' in recommended_df.columns: display_cols.append('reviews')
                    if '预估历史总产值' in recommended_df.columns: display_cols.append('预估历史总产值')
                    display_cols.extend(['进货底线价', '当前设置下ROI', '1688链接'])

                    st.dataframe(
                        recommended_df[display_cols],
                        column_config={
                            "image": st.column_config.ImageColumn("📸 主图 (右键复制)"),
                            "title": "西班牙语标题",
                            "price": st.column_config.NumberColumn("竞品售价", format="$%.2f"),
                            "reviews": st.column_config.NumberColumn("评价数 (热度)"),
                            "预估历史总产值": st.column_config.NumberColumn("🔥 预估产值", format="$%d"),
                            "进货底线价": st.column_config.NumberColumn("⚠️ 1688进货警戒线", format="$%.2f"),
                            "当前设置下ROI": st.column_config.NumberColumn("🚀 预估 ROI", format="%.0f%%"),
                            "1688链接": st.column_config.LinkColumn("🛒 去核价", display_text="图搜1688")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.error("❌ 在当前的价格区间和评价数要求下，找不到任何商品。")
            else:
                st.error("❌ 该价格区间内没有商品，请放宽左侧的售价范围。")
        else:
            st.warning("抓取的数据格式有误，没有找到价格信息。")
else:
    st.info("👈 请在左侧上传由爬虫抓取的 data.json 文件以启动上帝视角。")