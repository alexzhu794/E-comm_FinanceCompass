import streamlit as st
from datetime import datetime, timedelta
import logic_driver  
import data_manager   # 只为了在启动时调用 init_db()


# 1. 页面基础设置
st.set_page_config(
    page_title="Cash Flow Guardian",
    # page_icon="💰",
    layout="wide"
)

# 1. 数据库初始化
# 在应用启动时，确保数据库和表已创建
try:
    data_manager.init_db()
except Exception as e:
    st.error(f"数据库初始化失败: {e}")
    st.stop() # 如果数据库无法启动，停止应用

st.title("现金流守护者")
st.caption("一个专注于小商家现金流安全与预测的事务性模拟器")

# 2. 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择一个页面",
    ["◼️ 仪表盘", "◼️ 录入数据", "◼️ 管理 & 对账"]
)


# 页面一：仪表盘 (Dashboard) - (只读)
if page == "◼️ 仪表盘":
    st.header("实时仪表盘")
    st.info("数据实时计算。每次在“录入数据”页面操作后，这里的指标都会立即刷新。")

    # 1.1 获取核心指标
    # 调用 logic_driver.py 中的函数，获取所有需要展示的指标
    metrics = logic_driver.getDdashboardMetrics()
    
    col1, col2, col3 = st.columns(3)
    
    # 指标 1: 实时余额
    col1.metric(
        "实时银行余额", 
        f"¥ {metrics['current_balance']:,.2f}",
        help="这是您银行账户中的实时余额 (所有 'transactions' 表的总和)。"
    )
    
    # 指标 2: 安全接单数
    col2.metric(
        "安全接单数 (今日)", 
        f"{metrics['safe_orders_today']} 单",
        help=f"基于您 ¥{metrics['avg_cost_per_order']:.2f} 的平均垫付成本，您当前余额最多还能垫付 {metrics['safe_orders_today']} 单。"
    )
    
    # 指标 3: 平均成本
    col3.metric(
        "平均垫付成本",
        f"¥ {metrics['avg_cost_per_order']:,.2f}",
        help="您每笔订单 (未取消的) 需要垫付的平均成本。"
    )

    st.divider()

    # 历史趋势图
    st.subheader("历史趋势分析")

    col_hist_1, col_hist_2 = st.columns(2)

    with col_hist_1:
        st.write("银行余额变化图")
        balance_hist_df = logic_driver.getBalanceHistoryChartData()
        if not balance_hist_df.empty:
            st.line_chart(balance_hist_df.set_index('date_posted')['cumulative_balance'])
        else:
            st.info("尚无交易记录。")

    with col_hist_2:
        st.write("每日订单量 (F-OUT-5)")
        order_vol_df = logic_driver.getOrderVolumeChartData()
        if not order_vol_df.empty:
            st.line_chart(order_vol_df.set_index('date_created')['daily_order_count'])
        else:
            st.info("尚无订单记录。")

    st.divider() 

    # 1.2 获取未来回款日历
    st.subheader("未来30天待回款日历")
    
    payout_df = logic_driver.getPayoutChartData()
    
    if not payout_df.empty:
        # 重命名列以优化图表显示
        payout_df_renamed = payout_df.rename(columns={
            "expected_payout_date": "日期",
            "daily_payout_total": "待回款金额"
        }).set_index("日期")
        
        st.bar_chart(payout_df_renamed)
        st.caption("此图表只统计 'PENDING' 状态的订单。")
    else:
        st.info("尚无 'PENDING' 状态的订单，没有待回款。")



# 页面二：录入数据 (Entry) - (只写)
elif page == "◼️ 录入数据":
    st.header("录入新数据")

    # 2.1 录入新订单
    with st.form("new_order_form"):
        st.subheader("录入新订单")
        st.caption("这将自动在 'orders' 表创建记录，并在 'transactions' 表扣除垫付成本。")
        
        col1, col2 = st.columns(2)
        cost = col1.number_input("垫付成本 (Cost)", min_value=0.01, format="%.2f", help="您为这单垫付的钱 (负现金流)")
        profit = col2.number_input("预期利润 (Profit)", min_value=0.0, format="%.2f", help="这单成功后您赚的钱")
        
        submitted_order = st.form_submit_button("保存新订单")
        
        if submitted_order:
            # 调用 logic_driver.py 中的封装函数处理新订单录入
            success = logic_driver.HandleNewOrder(cost, profit)
            if success:
                st.success(f"订单已保存！成本 ¥{cost:.2f} 已从余额扣除。")
                st.balloons() # 🎈庆祝一下
            else:
                st.error("保存订单失败，请检查终端日志。")

    st.divider()

    # 2.2 录入平台回款
    with st.form("payout_form"):   
        st.subheader("录入平台回款")
        st.caption("这将自动在 'transactions' 表增加入账，并 '结清' (PAID) 对应日期的 PENDING 订单。")
        
        col1, col2, col3 = st.columns(3)
        payout_date = col1.date_input("回款到账日期", datetime.now())
        # 默认回款来自 15 天前
        default_original_date = datetime.now() - timedelta(days=data_manager.config.PAYOUT_DELAY_DAYS)
        original_date = col2.date_input("对应的原始订单日期", default_original_date)
        amount = col3.number_input("到账金额", min_value=0.01, format="%.2f")
        
        submitted_payout = st.form_submit_button("保存回款记录")
        
        if submitted_payout:
            # 将日期转换为 "YYYY-MM-DD" 字符串
            payout_date_str = payout_date.strftime('%Y-%m-%d')
            original_date_str = original_date.strftime('%Y-%m-%d')
            
            # 调用 "大脑"
            success = logic_driver.HandlePayout(payout_date_str, original_date_str, amount)
            if success:
                st.success(f"回款 ¥{amount:.2f} 已保存！余额已增加，{original_date_str} 的订单已结清。")
            else:
                st.error("保存回款失败，请检查终端日志。")
    
    st.divider()    # 用于在页面上添加分割线

    # 2.3 录入启动资金
    with st.form("capital_form"):
        st.subheader("录入启动资金 (通常只用一次)")
        amount_capital = st.number_input("启动资金金额", min_value=0.01, format="%.2f")
        
        submitted_capital = st.form_submit_button("注入资金")
        
        if submitted_capital:
            # 调用
            success = logic_driver.HandleInitialCapital(amount_capital)
            if success:
                st.success(f"启动资金 ¥{amount_capital:.2f} 已注入！")
            else:
                st.error("注入资金失败，请检查终端日志。")

    st.divider()

    # 2.4 录入固定支出
    with st.form("fixed_expense_form"):
        st.subheader("F-IN-4: 录入固定支出 (非订单)")
        st.caption("例如：SaaS 软件费、仓储费、广告费等。这将直接从您的银行余额中扣除。")

        # 从 config.py 读取模板
        import config 
        template_options = config.RECURRING_EXPENSE_TEMPLATES
        selected_template = st.selectbox(
            "选择支出模板",
            options=template_options,
            format_func=lambda x: f"{x['name']} (默认: ¥{x['default_amount']:.2f})"      # 显示名称和默认金额
        )

        # 如果选了 '自定义'，就用 number_input，否则用模板的默认值
        if selected_template['name'] == '自定义支出':
            expense_name = st.text_input("自定义支出名称", "")
            expense_amount = st.number_input("支出金额", min_value=0.01, format="%.2f")
        else:
            expense_name = selected_template['name']
            expense_amount = st.number_input("支出金额", value=selected_template['default_amount'], min_value=0.01, format="%.2f")

        submitted_expense = st.form_submit_button("保存这笔支出")

        if submitted_expense:
            if not expense_name:
                st.error("请输入支出名称。")
            else:
                success = logic_driver.HandleFixedExpense(expense_name, expense_amount)
                if success:
                    st.success(f"支出 '{expense_name}' (¥{expense_amount:.2f}) 已保存！")
                else:
                    st.error("保存支出失败。")



# 页面三：管理 & 对账 (Manage) - (读/改)
elif page == "◼️ 管理 & 对账":
    st.header("订单管理 & 银行流水")

    # 3.1 取消订单
    st.subheader("取消订单")
    st.caption("处理退款：设置状态，并选择是否退回了垫付成本、是否由您承担退货运费。")
    
    # 调用获取所有订单供选择
    orders_df_manage = logic_driver.getAllOrders()
    
    if orders_df_manage.empty:
        st.info("尚无订单记录。")
    else:
        # 只显示 "PENDING" 状态的订单，因为只有它们可以被取消
        pending_orders = orders_df_manage[orders_df_manage['status'] == 'PENDING']
        
        if pending_orders.empty:
            st.info("没有 'PENDING' 状态的订单可供取消。")
        else:
            # 使用 Selectbox 提供一个友好的选择器
            order_id_to_cancel = st.selectbox(
                "选择一笔 'PENDING' 订单将其设为 'CANCELLED' (退款)",
                options=pending_orders['order_id'],
                # format_func 提供了更易读的选项
                format_func=lambda x: f"ID: {x} (日期: {pending_orders.loc[pending_orders.order_id == x, 'date_created'].values[0]}, 成本: {pending_orders.loc[pending_orders.order_id == x, 'cost_advanced'].values[0]:.2f})"
            )

            col1, col2 = st.columns(2)
            cost_refunded = col1.checkbox("供应商已退回垫付成本？", help="勾选此项，垫付成本将退回您的银行余额。")
            seller_pays_shipping = col2.checkbox("您 (卖家) 承担退货运费？", help=f"勾选此项，将从余额扣除 {config.DEFAULT_RETURN_SHIPPING_FEE:.2f} 元运费。")
                
            if st.button("确认取消这笔订单", type="primary"):
                if order_id_to_cancel:
                    success = logic_driver.HandleCancelOrder(
                        int(order_id_to_cancel), 
                        cost_refunded, 
                        seller_pays_shipping
                    )
                    
                    if success:
                        st.success(f"订单 {order_id_to_cancel} 已成功设为 'CANCELLED'。")
                        st.rerun()   # 强制刷新页面以更新 selectbox
                    else:
                        st.error("取消订单失败，请检查终端日志。")
                else:
                    st.warning("请选择一笔订单。")

    st.divider()

    # 3.2 查看总表
    st.subheader("数据总表 (用于调试与对账)")
    
    with st.expander("查看：所有订单 (Orders) 总表"):
        st.dataframe(orders_df_manage, use_container_width=True)
    
    with st.expander("查看：所有银行流水 (Transactions) 总表"):
        trans_df = logic_driver.getAllTransactions()
        st.dataframe(trans_df, use_container_width=True)