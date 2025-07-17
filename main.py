# main.py (已更新)

import data_manager
import finance_calculator
import growth_predictor
import reporter
from datetime import datetime
import pandas as pd

def display_main_menu():
    """显示主菜单 (已恢复清晰的录入选项)"""
    print("\n" + "="*20 + " E-commerce 财务罗盘 " + "="*20)
    print("核心操作:")
    print("  1. 精细录入 (逐单输入)") # <--- 恢复
    print("  2. 快速录入 (单日总数)") # <--- 恢复
    print("  3. 管理提前回款记录")
    print("---")
    print("分析与报告:")
    print("  4. 生成最新综合报告 (含增长预测)")
    print("  5. 生成并保存财务图表")
    print("---")
    print("数据管理:")
    print("  6. 删除一日主数据")
    print("  7. 查看所有历史数据")
    print("---")
    print("  8. 退出程序")
    print("="*58)
    return input("请输入选项 (1-8): ")

def handle_generate_charts():
    """处理生成并保存图表的流程。"""
    print("\n--- 5. 生成并保存财务图表 ---")
    df_history = data_manager.load_all_data()
    if df_history.empty:
        print("\n数据库为空，无法生成图表。")
        return
        
    df_early = data_manager.load_all_early_payouts()
    df_calculated = finance_calculator.calculate_finances(df_history, df_early)
    
    # 调用 reporter 模块的函数来生成图表
    reporter.plot_financial_trends(df_calculated)


def get_date_input(prompt):
    """一个通用的、带验证的日期输入函数。"""
    while True:
        date_str = input(prompt)
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            print("日期格式错误，请输入YYYY-MM-DD 格式。")


# --- 功能 1 & 2: 精细录入 & 快速录入 ---
def get_common_inputs(is_quick_mode):
    """
    获取两种录入模式的通用输入部分。
    增加对退款金额和对应利润损失的估算。
    """
    date_str = get_date_input("请输入日期 (格式YYYY-MM-DD): ")

    if is_quick_mode:
        print("\n--- 2. 快速录入 (单日总数) ---")
        order_count = int(input("当日总订单数: "))
        total_cost = float(input("当日总成本: "))
        total_profit = float(input("当日总利润: "))
    else:
        print("\n--- 1. 精细录入 (逐单) ---")
        order_count = int(input("当日订单数: "))
        total_cost = 0.0
        total_profit = 0.0
        if order_count > 0:
            print(f"请逐一输入 {order_count} 笔订单的成本和利润:")
            for i in range(order_count):
                print(f"--- 订单 {i+1} ---")
                cost_str = input(f"  -> 成本: ")
                profit_str = input(f"  -> 利润: ")
                total_cost += float(cost_str)
                total_profit += float(profit_str)
    
    # 通用部分
    refunds = float(input("当日收到的退款金额 (默认为0): ") or 0)
    
    # 根据 "策略三" 计算估算的利润损失
    # 退款金额 * 平均利润率
    estimated_profit_loss_from_refunds = refunds * finance_calculator.AVERAGE_PROFIT_MARGIN


    other_income = float(input("当日其他店铺入账金额 (默认为0): ") or 0) 
    notes = input("备注 (可留空): ")
    
    # 确认
    print("\n--- 请确认输入 ---")
    print(f"日期: {date_str}, 总订单数: {order_count}")
    print(f"总成本: {total_cost:.2f}, 总利润: {total_profit:.2f}")
    print(f"退款额: {refunds:.2f} (估算利润损失: {estimated_profit_loss_from_refunds:.2f})") # 打印估算利润损失
    print(f"其他入账: {other_income:.2f}")
    print(f"备注: {notes}")
    confirm = input("以上信息是否正确? (y/n, 正确则保存): ")
    if confirm.lower() == 'y':
        return date_str, order_count, total_cost, total_profit, refunds, estimated_profit_loss_from_refunds, other_income, notes, True
    else:
        print("已取消操作。")
        return [None]*8 + [False]

def handle_manage_early_payouts():
    """提前回款管理的子菜单和逻辑分发"""
    while True:
        print("\n--- 管理提前回款 ---")
        print("  a. 新增一条提前回款")
        print("  b. 删除一条提前回款")
        print("  c. 查看所有提前回款")
        print("  d. 返回主菜单")
        choice = input("请选择操作 (a-d): ").lower()
        if choice == 'a': handle_add_early_payout()
        elif choice == 'b': handle_delete_early_payout()
        elif choice == 'c': handle_view_early_payouts()
        elif choice == 'd': break
        else: print("无效输入。")

def handle_add_early_payout():
    print("\n--- 新增提前回款 ---")
    try:
        payout_date = get_date_input("这笔钱是哪天收到的 (格式 YYYY-MM-DD): ")
        original_date_str = input("这笔钱对应的是哪天订单的回款 (格式 YYYY-MM-DD，不知道请直接回车): ")
        original_date = original_date_str if original_date_str else None
        
        if not original_date:
            print("注意：未指定来源日期，此笔款项将只作为现金流入，但无法抵扣未来应收款，可能导致未来资金预测偏高。")

        amount = float(input("提前收到的金额是多少: "))
        
        confirm_msg = f"确认在 {payout_date} 收到一笔来自 [{original_date or '未知来源'}] 的 {amount:.2f} 元回款吗? (y/n): "
        if input(confirm_msg).lower() == 'y':
            data_manager.save_early_payout(payout_date, original_date, amount)
    except (ValueError, TypeError):
        print("输入无效，金额必须是数字。")

def handle_view_early_payouts():
    print("\n--- 所有提前回款记录 ---")
    df_early = data_manager.load_all_early_payouts()
    if df_early.empty:
        print("尚无提前回款记录。")
    else:
        df_display = df_early.copy()
        df_display['Payout_Date'] = df_display['Payout_Date'].dt.strftime('%Y-%m-%d')
        df_display['Original_Order_Date'] = df_display['Original_Order_Date'].dt.strftime('%Y-%m-%d').fillna('未知来源')
        print(df_display.to_string(index=False))

def handle_delete_early_payout():
    handle_view_early_payouts()
    df_early = data_manager.load_all_early_payouts()
    if df_early.empty: return

    try:
        payout_id = int(input("\n请输入要删除记录的 payout_id: "))
        if input(f"确认要删除ID为 {payout_id} 的记录吗？(y/n): ").lower() == 'y':
            data_manager.delete_early_payout_by_id(payout_id)
    except ValueError:
        print("输入无效，ID必须是数字。")

def handle_add_data(is_quick_mode):
    """统一处理两种录入模式的流程。"""
    try:
        # --- 获取用户输入 ---
        date, count, cost, profit, refunds, estimated_profit_loss, other_income, notes, success = get_common_inputs(is_quick_mode)
        if not success: 
            return # 如果用户取消，直接返回

        # --- 检查并确认覆盖 ---
        if data_manager.check_date_exists(date):
            overwrite = input(f"警告：日期 {date} 的数据已存在，是否要覆盖？ (y/n): ")
            if overwrite.lower() != 'y':
                print("操作已取消。")
                return
        
        # --- 保存数据到数据库 ---
        data_manager.save_daily_data(date, count, cost, profit, refunds, estimated_profit_loss, other_income, notes)

    except (ValueError, TypeError):
        # 这个 except 只捕获用户输入时的数字格式错误
        print("\n[错误] 输入无效，订单数/成本/利润/退款等字段必须是数字。请重新操作。")
    except Exception as e:
        # 这个 except 捕获所有其他意外错误，特别是数据库错误
        print(f"\n[严重错误] 程序在执行时遇到问题: {e}")
        print("这很可能是由于数据库文件结构与当前代码不匹配导致的。")
        print(">>> 解决方案：请务必退出程序，删除项目文件夹下的 'finance_compass.db' 文件，然后重新运行。")



# --- 其他功能函数 ---
def handle_delete():
    print("\n--- 4. 删除一日主数据 ---")
    date_str = get_date_input("请输入要删除数据的日期 (格式YYYY-MM-DD): ")
    if data_manager.check_date_exists(date_str):
        confirm = input(f"确认要删除 {date_str} 的所有主数据吗？此操作不可逆！(y/n): ")
        if confirm.lower() == 'y':
            data_manager.delete_data_by_date(date_str)
    else:
        print("该日期不存在，无法删除。")


def handle_view_all():
    print("\n--- 历史财务状况一览表 ---")
    df_raw = data_manager.load_all_data()
    if df_raw.empty:
        print("数据库中尚无主数据。")
        return

    df_early = data_manager.load_all_early_payouts()
    df_calculated = finance_calculator.calculate_finances(df_raw, df_early)

    # 显示列调整，加入 Estimated_Profit_Loss_From_Refunds
    display_cols = ['Date', 'Daily_Order_Count', 'Total_Daily_Cost', 'Total_Daily_Profit', 
                    'Refunds_Received_Today', 'Estimated_Profit_Loss_From_Refunds', # 显示利润损失
                    'Other_Income_Today', 'daily_actual_inflow', 'daily_net_cash_flow', 'bank_balance', 'cumulative_profit'] # 显示累计利润
    
    df_display = df_calculated[display_cols].copy()
    df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')
    currency_cols = [col for col in display_cols if col not in ['Date', 'Daily_Order_Count']]
    for col in currency_cols:
        df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}")
    
    pd.set_option('display.max_rows', None); pd.set_option('display.max_columns', None); pd.set_option('display.width', 1000)
    print(df_display.to_string(index=False))


def display_latest_report():
    print("\n--- 最新综合报告 (含增长预测) ---")
    df_history = data_manager.load_all_data()
    df_early = data_manager.load_all_early_payouts()
    if df_history.empty and df_early.empty:
        print("\n数据库为空，无报告可生成。")
        return
        
    df_calculated = finance_calculator.calculate_finances(df_history, df_early)
    if df_calculated.empty: return
        
    latest_data = df_calculated.iloc[-1]
    
    print("\n" + "="*20 + " 财务状况 " + "="*20)
    print(f"数据截止日期: {latest_data['Date'].strftime('%Y-%m-%d')}")
    print(f"当前银行总余额: {latest_data['bank_balance']:,.2f} 元")
    print(f"当前累计总利润: {latest_data['cumulative_profit']:,.2f} 元")
    
    # --- 集成增长预测 ---
    print("\n" + "="*20 + " 增长预测 " + "="*20)
    # 调用预测模块
    prediction = growth_predictor.analyze_growth(df_calculated, finance_calculator.PAYOUT_DELAY_DAYS)

    if prediction["status"] == "ok":
        print(f"当前模式稳定后，日均净现金流: {prediction['avg_daily_net_cash_flow']:+.2f} 元")
        print(f"下一个增单目标: {prediction['target_order_count']} 单/天")
        print(f"预计还需积累天数: {prediction['days_to_next_increment']:.1f} 天")
        print(f"预计可在【{prediction['predicted_date_for_increment'].strftime('%Y-%m-%d')}】安全增单")
    else:
        # 打印 "calculating" 或 "warning" 状态信息
        print(prediction["message"])
        
    print("\n" + "="*20 + " 截止日详情 " + "="*19)
    print(f"订单: {latest_data['Daily_Order_Count']} 单, 总成本: {latest_data['Total_Daily_Cost']:.2f}, 总利润: {latest_data['Total_Daily_Profit']:.2f}")
    print(f"退款: {latest_data['Refunds_Received_Today']:.2f} (利润损失估算: {latest_data['Estimated_Profit_Loss_From_Refunds']:.2f})")
    print(f"其他入账: {latest_data['Other_Income_Today']:.2f}")
    print(f"当日净现金流: {latest_data['daily_net_cash_flow']:+.2f}")
    print("="*58)


def main():
    """主函数 (已恢复清晰的选项分发)"""
    data_manager.init_db()
    
    while True:
        choice = display_main_menu()
        if choice == '1': handle_add_data(is_quick_mode=False) # <--- 明确调用精细模式
        elif choice == '2': handle_add_data(is_quick_mode=True)  # <--- 明确调用快速模式
        elif choice == '3': handle_manage_early_payouts()
        elif choice == '4': display_latest_report()
        elif choice == '5': handle_generate_charts()
        elif choice == '6': handle_delete()
        elif choice == '7': handle_view_all()
        elif choice == '8':
            print("感谢使用，程序退出。")
            break
        else:
            print("无效输入。")


if __name__ == "__main__":
    main()
