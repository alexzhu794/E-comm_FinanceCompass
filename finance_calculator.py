# finance_calculator.py (已更新)

import pandas as pd
from datetime import timedelta

PAYOUT_DELAY_DAYS = 15
INITIAL_CASH = 3000.0
AVERAGE_PROFIT_MARGIN = 0.25 

def calculate_finances(df_daily: pd.DataFrame, df_early_payouts: pd.DataFrame) -> pd.DataFrame:
    """
    根据主数据和提前回款数据，重新计算整个历史记录的财务指标。
    核心升级：基于完整的日期范围进行计算，确保数据连续性。
    """
    if df_daily.empty and df_early_payouts.empty:
        return pd.DataFrame()

    # --- 核心升级：创建完整的日期范围 ---
    all_dates = []
    if not df_daily.empty:
        all_dates.extend(df_daily['Date'].tolist())
    if not df_early_payouts.empty:
        all_dates.extend(df_early_payouts['Payout_Date'].tolist())
    
    if not all_dates:
        return pd.DataFrame()

    min_date, max_date = min(all_dates), max(all_dates)
    full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    df_calculated = pd.DataFrame(full_date_range, columns=['Date'])
    
    # 将原始数据合并到完整的日期范围上
    if not df_daily.empty:
        df_calculated = pd.merge(df_calculated, df_daily, on='Date', how='left')
    
    # 将所有NaN值填充为0，因为这些天没有订单或记录
    fill_cols = ['Daily_Order_Count', 'Total_Daily_Cost', 'Total_Daily_Profit', 
                 'Refunds_Received_Today', 'Estimated_Profit_Loss_From_Refunds', 
                 'Other_Income_Today']
    for col in fill_cols:
        if col not in df_calculated.columns:
            df_calculated[col] = 0
    df_calculated[fill_cols] = df_calculated[fill_cols].fillna(0)
    # ------------------------------------

    # 后续计算逻辑与之前类似，但现在基于 df_calculated
    df = df_calculated # 使用新创建的完整DataFrame
    
    # ... (从这里开始的计算逻辑与上一个版本完全相同)
    for col in ['daily_outflow', 'daily_actual_inflow', 'daily_net_cash_flow', 'bank_balance', 'daily_profit', 'cumulative_profit']:
        df[col] = 0.0

    df.set_index('Date', inplace=True)
    
    early_payouts_received_on_date = pd.Series()
    early_payouts_deducted_from_date = pd.Series()
    if not df_early_payouts.empty:
        early_payouts_received_on_date = df_early_payouts.groupby('Payout_Date')['Amount'].sum()
        # 在计算扣除额时，只考虑有明确原始日期的记录
        known_origin_payouts = df_early_payouts.dropna(subset=['Original_Order_Date'])
        if not known_origin_payouts.empty:
            early_payouts_deducted_from_date = known_origin_payouts.groupby('Original_Order_Date')['Amount'].sum()

    for i in range(len(df)):
        current_date = df.index[i]
        
        df.loc[current_date, 'daily_outflow'] = df.loc[current_date, 'Total_Daily_Cost']

        inflow_date = current_date - timedelta(days=PAYOUT_DELAY_DAYS)
        net_scheduled_inflow = 0.0
        if inflow_date in df.index:
            gross_scheduled_inflow = df.loc[inflow_date, 'Total_Daily_Cost'] + df.loc[inflow_date, 'Total_Daily_Profit']
            deductions = early_payouts_deducted_from_date.get(inflow_date, 0)
            net_scheduled_inflow = gross_scheduled_inflow - deductions

        today_early_payouts = early_payouts_received_on_date.get(current_date, 0)
        today_refunds = df.loc[current_date, 'Refunds_Received_Today']
        today_other_income = df.loc[current_date, 'Other_Income_Today']
        
        daily_actual_inflow = net_scheduled_inflow + today_early_payouts + today_refunds + today_other_income
        df.loc[current_date, 'daily_actual_inflow'] = daily_actual_inflow

        df.loc[current_date, 'daily_net_cash_flow'] = daily_actual_inflow - df.loc[current_date, 'daily_outflow']
        
        previous_balance = INITIAL_CASH if i == 0 else df.loc[df.index[i-1], 'bank_balance']
        df.loc[current_date, 'bank_balance'] = previous_balance + df.loc[current_date, 'daily_net_cash_flow']

        df.loc[current_date, 'daily_profit'] = df.loc[current_date, 'Total_Daily_Profit']
        
        previous_cumulative_profit = 0.0 if i == 0 else df.loc[df.index[i-1], 'cumulative_profit']
        daily_estimated_profit_loss = df.loc[current_date, 'Estimated_Profit_Loss_From_Refunds']
        df.loc[current_date, 'cumulative_profit'] = previous_cumulative_profit + df.loc[current_date, 'daily_profit'] - daily_estimated_profit_loss

    df.reset_index(inplace=True)
    return df
