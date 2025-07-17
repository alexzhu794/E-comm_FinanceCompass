# growth_predictor.py

import pandas as pd
from datetime import timedelta

# --- 增长策略相关的固定参数 ---
# 增加1单需要的额外缓冲资金 (用来覆盖新单的15天空窗期垫付)
INCREMENT_ORDER_BUFFER_PER_UNIT = 900.0

def analyze_growth(df_calculated: pd.DataFrame, payout_delay_days: int) -> dict:
    """
    分析财务数据并预测下一个增长点。
    :param df_calculated: 包含完整财务计算结果的DataFrame。
    :param payout_delay_days: 支付延迟天数，用于确定稳定期。
    :return: 一个包含预测结果的字典。
    """
    
    # 至少需要一个完整的支付周期 + 1天的数据才能进行有意义的预测
    if len(df_calculated) <= payout_delay_days:
        return {
            "status": "calculating",
            "message": "数据不足，至少需要运营超过一个回款周期才能进行预测..."
        }

    # 1. 确定稳定期 (从第 payout_delay_days + 1 天开始)
    stable_period_df = df_calculated.iloc[payout_delay_days:]
    
    if stable_period_df.empty:
        return {
            "status": "calculating",
            "message": "已度过第一个回款周期，正在积累稳定期数据..."
        }

    # 2. 计算稳定期的日均净现金流 (这是你每天能攒下的钱)
    avg_daily_net_cash_flow = stable_period_df['daily_net_cash_flow'].mean()

    # 如果日均净现金流为负或零，说明在亏钱或持平，无法支持增单
    if avg_daily_net_cash_flow <= 0:
        return {
            "status": "warning",
            "message": f"警告：稳定期内日均净现金流为负 ({avg_daily_net_cash_flow:.2f}元/天)，当前模式无法支持增单。"
        }
    
    # 获取最新数据
    latest_data = df_calculated.iloc[-1]
    current_date = latest_data['Date']
    current_bank_balance = latest_data['bank_balance']

    # 3. 计算从当前银行余额开始，还需要多少缓冲资金
    needed_buffer = INCREMENT_ORDER_BUFFER_PER_UNIT
    
    # 这里的逻辑是：增单需要的总缓冲金是固定的 (900元)
    # 我们可以简化为：需要多少天才能攒够这900元
    
    # 4. 计算所需积累天数
    days_to_accumulate = needed_buffer / avg_daily_net_cash_flow

    # 5. 预测下一个增单日期
    # 预测日期 = 当前日期 + 积累所需天数
    # 这里我们不需要再加 payout_delay_days，因为缓冲金的设计已经覆盖了那个风险
    predicted_date = current_date + timedelta(days=days_to_accumulate)
    
    # 获取当前订单数，计算目标订单数
    current_order_count = latest_data['Daily_Order_Count']
    target_order_count = current_order_count + 1

    return {
        "status": "ok",
        "message": "已生成预测",
        "avg_daily_net_cash_flow": avg_daily_net_cash_flow,
        "days_to_next_increment": days_to_accumulate,
        "predicted_date_for_increment": predicted_date,
        "target_order_count": target_order_count
    }
