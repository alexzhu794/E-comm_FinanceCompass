# reporter.py (已更新)

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os


# 定义图表保存的文件夹
#CHARTS_DIR = 'charts'

def set_chinese_font():
    """
    智能查找并设置支持中文的字体（正确且完整的版本）。
    """
    # 常见的中文字体列表 (Windows, macOS, Linux)
    # 将最可能存在的字体放在前面，提高效率
    font_names = [
        'Microsoft YaHei',  # Windows 系统
        'SimHei',           # 通用黑体
        'Heiti TC',         # macOS 系统
        'WenQuanYi Micro Hei', # Linux 系统
        'sans-serif'        # 最后的备用选项
    ]
    
    # 核心逻辑：逐个尝试，直到找到一个可用的中文字体
    for font_name in font_names:
        try:
            # 尝试设置字体
            plt.rcParams['font.sans-serif'] = [font_name]
            # 解决负号'-'显示为方块的问题
            plt.rcParams['axes.unicode_minus'] = False 
            # 如果上一行代码没有报错，说明字体找到了，直接返回，不再继续尝试
            # 我们不在这个模块里打印信息，而是由调用它的 app.py 决定是否打印
            return
        except Exception:
            # 如果这个字体找不到，就静默地继续尝试下一个
            continue
            
    # 如果循环结束后仍然没有成功设置字体，可以在调用方 (app.py) 中给出警告
    # 这里函数本身不需要做任何事
            

'''
def ensure_charts_dir():
    """确保用于保存图表的文件夹存在。"""
    if not os.path.exists(CHARTS_DIR):
        os.makedirs(CHARTS_DIR)
'''

def plot_financial_trends(df_calculated: pd.DataFrame) -> list:
    """
    生成所有核心财务趋势图表，并返回Matplotlib figure对象列表。
    :param df_calculated: 包含完整财务计算结果的DataFrame。
    :return: 一个包含 (标题, figure对象) 元组的列表。
    """
    if df_calculated.empty or len(df_calculated) < 2:
        return []

    set_chinese_font()
    
    figs = []

    # --- 1. 银行账户现金余额趋势图 ---
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df_calculated['Date'], df_calculated['bank_balance'], marker='o', linestyle='-', color='b')
    ax1.set_title('银行账户现金余额趋势', fontsize=16)
    ax1.set_xlabel('日期', fontsize=12)
    ax1.set_ylabel('余额 (元)', fontsize=12)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
    fig1.autofmt_xdate()
    figs.append(('银行账户现金余额趋势', fig1))

    # --- 2. 每日净现金流图 ---
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    colors = ['g' if x >= 0 else 'r' for x in df_calculated['daily_net_cash_flow']]
    ax2.bar(df_calculated['Date'], df_calculated['daily_net_cash_flow'], color=colors)
    ax2.set_title('每日净现金流', fontsize=16)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_ylabel('净现金流 (元)', fontsize=12)
    ax2.axhline(0, color='grey', linewidth=0.8)
    fig2.autofmt_xdate()
    figs.append(('每日净现金流', fig2))

    # --- 3. 累计总利润趋势图 ---
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.plot(df_calculated['Date'], df_calculated['cumulative_profit'], marker='o', linestyle='-', color='purple')
    ax3.set_title('累计总利润趋势', fontsize=16)
    ax3.set_xlabel('日期', fontsize=12)
    ax3.set_ylabel('累计利润 (元)', fontsize=12)
    ax3.grid(True, which='both', linestyle='--', linewidth=0.5)
    fig3.autofmt_xdate()
    figs.append(('累计总利润趋势', fig3))
    
    return figs

    
    '''
    # --- 1. 银行账户现金余额趋势图 (折线图) ---
    plt.figure(figsize=(12, 7)) # 稍微增加高度以容纳日期
    plt.plot(df_calculated['Date'], df_calculated['bank_balance'], marker='o', linestyle='-', color='b')
    plt.title('银行账户现金余额趋势', fontsize=16) # <--- 已改为中文
    plt.xlabel('日期', fontsize=12) # <--- 已改为中文
    plt.ylabel('余额 (元)', fontsize=12) # <--- 已改为中文
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.gcf().autofmt_xdate() # 自动旋转日期标签

    # *** 第二步：在保存前调用 tight_layout() ***
    plt.tight_layout()
    
    balance_chart_path = os.path.join(CHARTS_DIR, 'bank_balance_trend.png')
    plt.savefig(balance_chart_path)
    plt.close()
    print(f"图表已保存到: {balance_chart_path}")

    # --- 2. 每日净现金流图 (柱状图) ---
    plt.figure(figsize=(12, 7))
    colors = ['g' if x >= 0 else 'r' for x in df_calculated['daily_net_cash_flow']]
    plt.bar(df_calculated['Date'], df_calculated['daily_net_cash_flow'], color=colors)
    plt.title('每日净现金流', fontsize=16) # <--- 已改为中文
    plt.xlabel('日期', fontsize=12) # <--- 已改为中文
    plt.ylabel('净现金流 (元)', fontsize=12) # <--- 已改为中文
    plt.axhline(0, color='grey', linewidth=0.8)
    plt.grid(True, axis='y', linestyle='--', linewidth=0.5)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.gcf().autofmt_xdate()

    # *** 第二步：在保存前调用 tight_layout() ***
    plt.tight_layout()

    cashflow_chart_path = os.path.join(CHARTS_DIR, 'daily_net_cash_flow.png')
    plt.savefig(cashflow_chart_path)
    plt.close()
    print(f"图表已保存到: {cashflow_chart_path}")

    # --- 3. 累计总利润趋势图 (折线图) ---
    plt.figure(figsize=(12, 7))
    plt.plot(df_calculated['Date'], df_calculated['cumulative_profit'], marker='o', linestyle='-', color='purple')
    plt.title('累计总利润趋势', fontsize=16) # <--- 已改为中文
    plt.xlabel('日期', fontsize=12) # <--- 已改为中文
    plt.ylabel('累计利润 (元)', fontsize=12) # <--- 已改为中文
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.gcf().autofmt_xdate()

    # *** 第二步：在保存前调用 tight_layout() ***
    plt.tight_layout()

    profit_chart_path = os.path.join(CHARTS_DIR, 'cumulative_profit_trend.png')
    plt.savefig(profit_chart_path)
    plt.close()
    print(f"图表已保存到: {profit_chart_path}")

    print("\n所有图表生成完毕！")
    '''
