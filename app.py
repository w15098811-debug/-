import streamlit as st
import pandas as pd
import json
import urllib.parse

st.set_page_config(page_title="ML 选品决策大脑", layout="wide", page_icon="🧠")
st.title("🧠 ML 跨境选品决策大脑 (Pro 版)")

# ==========================================
# 🚀 升级 1：支持本地/合伙人上传数据文件
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

# 🚀 升级 2：更精细的过滤条件
st.sidebar.markdown("---")
st.sidebar.header("🛡️ 3. 精细化选品漏斗")

col_a, col_b = st.sidebar.columns(2)
min_price = col_a.number_input("最低售价 (过滤低价卷王)", value=100)
max_price = col_b.number_input("最高售价 (过滤天价品)", value=5000)

target_margin = st.sidebar.slider("底线净利率 (%)", 5, 50, 15) / 100
target_roi = st.sidebar.slider("底线 ROI 投资回报率 (%)", 10, 200, 50) / 100
min_reviews = st.sidebar.number_input("最低评价数 (验证市场需求)", value=10)
only_full = st.sidebar.checkbox("只看 Full 仓竞品 (对标头部)", value=False)

# ==========================================
# 🧠 数据处理与看板展示
# ==========================================
if uploaded_file is not None:
    # 读取合伙人上传的文件
    raw_data = json.load(uploaded_file)
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        
        if 'price' in df.columns:
            # 数据清洗与售价过滤
            df = df[(df['price'] >= min_price) & (df['price'] <= max_price)].copy()
            
            if not df.empty:
                # 🚀 升级 3：更专业的财务核算 (加入 ROI 和 预估坑产)
                df['预估单件净利'] = df['price'] * target_margin
                # 进货底线价 = 售价 - 佣金 - 运费 - 你想要的利润
                df['进货底线价'] = df['price'] - (df['price'] * ml_fee) - shipping_cost - df['预估单件净利']
                
                # ROI (Return on Investment) = 净利 / 进货与物流成本
                # 只有进货价大于 0 时才计算 ROI
                df['当前设置下ROI'] = df.apply(
                    lambda row: (row['预估单件净利'] / (row['进货底线价'] + shipping_cost)) if row['进货底线价'] > 0 else 0, 
                    axis=1
                )
                
                # 预估总坑产 (售价 * 评价数) 作为该链接历史销售额的一个参考指标
                if 'reviews' in df.columns:
                    df['预估历史总产值'] = df['price'] * df['reviews']
                
                # 应用所有漏斗过滤
                if 'reviews' in df.columns:
                    df = df[df['reviews'] >= min_reviews]
                if only_full and 'shipping' in df.columns:
                    df = df[df['shipping'] == "Full (官方仓)"]
                
                # 核心筛选：必须有进货空间，且 ROI 达标
                recommended_df = df[(df['进货底线价'] > 0) & (df['当前设置下ROI'] >= target_roi)].copy()

                # --- 界面展示 ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📦 样本量 (价格区间内)", len(df))
                col2.metric("🎯 漏斗幸存潜力款", len(recommended_df))
                if not recommended_df.empty:
                    col3.metric("💰 幸存款均价", f"${recommended_df['price'].mean():.2f}")
                    col4.metric("🔥 最高预估产值", f"${recommended_df['预估历史总产值'].max():,.0f}")

                st.markdown("---")

                if not recommended_df.empty:
                    st.subheader("📋 高潜供应链清单 (按 ROI 排序)")
                    
                    # 生成 1688 图搜通用链接
                    recommended_df['1688链接'] = "https://www.1688.com/"
                    recommended_df = recommended_df.sort_values(by='当前设置下ROI', ascending=False)
                    
                    display_cols = ['image', 'title', 'price']
                    if 'reviews' in recommended_df.columns: display_cols.append('reviews')
                    if '预估历史总产值' in recommended_df.columns: display_cols.append('预估历史总产值')
                    display_cols.extend(['进货底线价', '当前设置下ROI', '1688链接'])

                    st.dataframe(
                        recommended_df[display_cols],
                        column_config={
                            "image": st.column_config.ImageColumn("📸 主图 (右键复制)", help="复制去1688搜同款"),
                            "title": "西班牙语标题",
                            "price": st.column_config.NumberColumn("竞品售价", format="$%.2f"),
                            "reviews": st.column_config.NumberColumn("评价数 (热度)"),
                            "预估历史总产值": st.column_config.NumberColumn("🔥 预估历史产值", format="$%d"),
                            "进货底线价": st.column_config.NumberColumn("⚠️ 最高进货警戒线", format="$%.2f"),
                            "当前设置下ROI": st.column_config.NumberColumn("🚀 预估 ROI", format="%.0f%%"),
                            "1688链接": st.column_config.LinkColumn("🛒 去进货", display_text="图搜1688")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.error("❌ 在当前的【目标利润】与【底线 ROI】要求下，没有符合条件的商品。")
            else:
                st.error("❌ 该价格区间内没有商品，请调整左侧的售价范围。")
        else:
            st.warning("抓取的数据格式有误，没有找到价格信息。")
else:
    st.info("👈 请在左侧上传由爬虫抓取的 data.json 文件以启动分析大脑。")