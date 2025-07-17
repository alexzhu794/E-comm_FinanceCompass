# app.py (最终修正版)

import streamlit as st
import pandas as pd
from datetime import datetime, date

# 导入我们自己的模块
import data_manager
import finance_calculator
import growth_predictor
import reporter

# --- 页面基础设置 ---
st.set_page_config(
    page_title="E-commerce 财务罗盘",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 E-commerce 财务罗盘")
st.caption("一个根据实际运营数据，提供财务分析与增长建议的智能助手。")

# 初始化数据库
data_manager.init_db()

# --- 侧边栏导航 (最终版) ---
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择一个页面",
    ["📊 仪表盘 & 报告", "✍️ 录入每日数据", "📈 管理提前回款", "🗑️ 删除每日数据"] # <-- 最终页面结构
)

# --- 全局数据加载 ---
@st.cache_data
def load_data():
    """加载所有数据并缓存"""
    df_history = data_manager.load_all_data()
    df_early = data_manager.load_all_early_payouts()
    return df_history, df_early

df_history, df_early = load_data()

# 计算财务数据
if not df_history.empty or not df_early.empty:
    df_calculated = finance_calculator.calculate_finances(df_history.copy(), df_early.copy())
else:
    df_calculated = pd.DataFrame()


# ==============================================================================
# 页面一：仪表盘 & 报告
# ==============================================================================
if page == "📊 仪表盘 & 报告":
    st.header("📊 仪表盘 & 报告")

    if df_calculated.empty:
        st.warning("尚无数据，请先在“录入每日数据”页面添加数据。")
    else:
        latest_data = df_calculated.iloc[-1]
        
        # 关键指标
        st.subheader("最新财务快照")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("数据截止日期", latest_data['Date'].strftime('%Y-%m-%d'))
        col2.metric("当前银行余额", f"¥{latest_data['bank_balance']:,.2f}")
        col3.metric("当前累计利润", f"¥{latest_data['cumulative_profit']:,.2f}")
        col4.metric("当日净现金流", f"¥{latest_data['daily_net_cash_flow']:,.2f}")

        # 增长预测
        st.subheader("🚀 增长预测")
        with st.container(border=True):
            prediction = growth_predictor.analyze_growth(df_calculated, finance_calculator.PAYOUT_DELAY_DAYS)
            if prediction["status"] == "ok":
                st.success("状态：可预测")
                col1, col2, col3 = st.columns(3)
                col1.metric("稳定期日均净现金流", f"¥{prediction['avg_daily_net_cash_flow']:,.2f}")
                col2.metric("预计增单所需天数", f"{prediction['days_to_next_increment']:.1f} 天")
                col3.metric("下一个增单日期", prediction['predicted_date_for_increment'].strftime('%Y-%m-%d'))
            else:
                st.info(f"状态：{prediction['message']}")

        # 可视化图表
        st.subheader("📈 财务趋势图")
        figs = reporter.plot_financial_trends(df_calculated)
        if figs:
            for title, fig in figs:
                with st.expander(f"查看 **{title}**", expanded=True):
                    st.pyplot(fig)
        else:
            st.info("数据不足，无法生成图表。")

        # 详细历史数据
        st.subheader("📜 详细历史数据")
        with st.expander("点击展开/折叠详细数据表"):
            st.dataframe(df_calculated)


# ==============================================================================
# 页面二：录入每日数据
# ==============================================================================
elif page == "✍️ 录入每日数据":
    st.header("✍️ 录入每日数据")

    entry_mode = st.radio(
        "请选择录入模式",
        ("精细录入 (逐单)", "快速录入 (汇总)"),
        horizontal=True
    )

    with st.form("daily_entry_form"):
        st.subheader("订单与成本")
        input_date = st.date_input("选择日期", value=date.today())
        
        if entry_mode == "精细录入 (逐单)":
            order_count = st.number_input("当日订单数", min_value=0, step=1)
            total_cost, total_profit = 0.0, 0.0
            if order_count > 0:
                for i in range(order_count):
                    col1, col2 = st.columns(2)
                    cost = col1.number_input(f"订单 {i+1} 成本", key=f"cost_{i}", min_value=0.0, format="%.2f")
                    profit = col2.number_input(f"订单 {i+1} 利润", key=f"profit_{i}", min_value=0.0, format="%.2f")
                    total_cost += cost
                    total_profit += profit
        else:
            order_count = st.number_input("当日总订单数", min_value=0, step=1)
            total_cost = st.number_input("当日总成本", min_value=0.0, format="%.2f")
            total_profit = st.number_input("当日总利润", min_value=0.0, format="%.2f")

        st.subheader("其他财务项目")
        refunds = st.number_input("当日收到的退款金额", min_value=0.0, format="%.2f")
        other_income = st.number_input("当日其他店铺入账金额", min_value=0.0, format="%.2f")
        notes = st.text_area("备注 (可选)")

        submitted = st.form_submit_button("保存当日数据")

    if submitted:
        date_str = input_date.strftime('%Y-%m-%d')
        est_loss = refunds * finance_calculator.AVERAGE_PROFIT_MARGIN
        
        if data_manager.check_date_exists(date_str):
            st.warning(f"日期 {date_str} 的数据已存在。保存将覆盖原有数据。")
        
        data_manager.save_daily_data(date_str, order_count, total_cost, total_profit, refunds, est_loss, other_income, notes)
        st.success(f"日期 {date_str} 的数据已成功保存！页面将刷新以展示最新数据。")
        st.balloons()
        st.cache_data.clear()
        st.rerun()


# ==============================================================================
# 页面三：管理提前回款 (已恢复并增强)
# ==============================================================================
elif page == "📈 管理提前回款":
    st.header("📈 管理提前回款记录")

    # --- 1. 新增提前回款 ---
    with st.form("early_payout_form"):
        st.subheader("新增一条记录")
        payout_date = st.date_input("回款收款日期", value=date.today())
        
        has_original_date = st.checkbox("是否知道来源订单日期？")
        original_order_date = None
        if has_original_date:
            original_order_date = st.date_input("来源订单日期")
        
        amount = st.number_input("提前回款金额", min_value=0.01, format="%.2f")
        
        submitted_payout = st.form_submit_button("保存提前回款记录")

    if submitted_payout:
        payout_date_str = payout_date.strftime('%Y-%m-%d')
        original_date_str = original_order_date.strftime('%Y-%m-%d') if original_order_date else None
        data_manager.save_early_payout(payout_date_str, original_date_str, amount)
        st.success("提前回款记录已保存！页面将刷新。")
        st.cache_data.clear()
        st.rerun()
    
    st.divider()

    # --- 2. 查看和删除提前回款 ---
    st.subheader("现有记录")
    if df_early.empty:
        st.info("尚无提前回款记录。")
    else:
        st.dataframe(df_early)
        
        st.write("要删除记录，请从下方选择ID：")
        payout_ids = df_early['payout_id'].tolist()
        id_to_delete = st.selectbox(
            "选择要删除记录的payout_id",
            options=payout_ids,
            index=None,
            placeholder="请选择一个ID..."
        )

        if id_to_delete:
            if st.button(f"确认删除ID为【{id_to_delete}】的记录", type="primary"):
                success = data_manager.delete_early_payout_by_id(id_to_delete)
                if success:
                    st.success(f"ID {id_to_delete} 的记录已成功删除！页面将刷新。")
                    st.cache_data.clear()
                    st.rerun()


# ==============================================================================
# 页面四：删除每日数据 (全新独立页面)
# ==============================================================================
elif page == "🗑️ 删除每日数据":
    st.header("🗑️ 删除每日数据")
    st.warning("️警告：此操作不可逆，将永久删除选定日期的所有订单、成本、退款等主数据！")

    if df_history.empty:
        st.info("没有可供删除的每日数据。")
    else:
        dates_with_data = df_history['Date'].dt.strftime('%Y-%m-%d').tolist()
        date_to_delete = st.selectbox(
            "选择要删除数据的日期",
            options=sorted(dates_with_data, reverse=True), # 日期倒序排列，方便选择最近的
            index=None,
            placeholder="请选择一个日期..."
        )
        
        if date_to_delete:
            if st.button(f"永久删除【{date_to_delete}】的所有数据", type="primary"):
                data_manager.delete_data_by_date(date_to_delete)
                st.success(f"日期 {date_to_delete} 的数据已成功删除！页面将刷新。")
                st.cache_data.clear()
                st.rerun()
