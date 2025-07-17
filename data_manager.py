# data_manager.py (已更新)

import sqlite3
import pandas as pd
import os

DB_FILE = 'finance_compass.db'
DAILY_TABLE = 'daily_data'
EARLY_PAYOUT_TABLE = 'early_payouts'


def init_db():
    """初始化数据库。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 主数据表 (无变化)
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {DAILY_TABLE} (
            Date TEXT PRIMARY KEY, Daily_Order_Count INTEGER, Total_Daily_Cost REAL,
            Total_Daily_Profit REAL, Refunds_Received_Today REAL, 
            Estimated_Profit_Loss_From_Refunds REAL, Other_Income_Today REAL, Notes TEXT
        )
    ''')
    
    # 提前回款表 (结构重大更新)
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {EARLY_PAYOUT_TABLE} (
            payout_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 新增唯一ID
            Payout_Date TEXT NOT NULL,
            Original_Order_Date TEXT, -- 允许为空 (NULL)
            Amount REAL NOT NULL
        )
    ''')
    print("数据库初始化完成，所有表已准备就绪。")
    conn.commit()
    conn.close()

def check_date_exists(date_str):
    """检查指定日期的数据是否已存在于主数据表中。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"SELECT COUNT(1) FROM {DAILY_TABLE} WHERE Date = ?", (date_str,))
    exists = c.fetchone()[0] > 0
    conn.close()
    return exists

# save_daily_data 函数参数和SQL语句需要更新
def save_daily_data(date_str, order_count, total_cost, total_profit, refunds, estimated_profit_loss_from_refunds, other_income, notes):
    """将单日数据保存或更新到主数据表中。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f'''
        INSERT OR REPLACE INTO {DAILY_TABLE} (Date, Daily_Order_Count, Total_Daily_Cost, Total_Daily_Profit, 
                                            Refunds_Received_Today, Estimated_Profit_Loss_From_Refunds, Other_Income_Today, Notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date_str, order_count, total_cost, total_profit, refunds, estimated_profit_loss_from_refunds, other_income, notes))
    conn.commit()
    conn.close()
    print(f"日期 {date_str} 的主数据已成功保存。")

# save_early_payout 参数和SQL语句需要更新
def save_early_payout(payout_date, original_order_date, amount):
    """保存一条提前回款记录。original_order_date 可以为 None。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f'''
        INSERT INTO {EARLY_PAYOUT_TABLE} (Payout_Date, Original_Order_Date, Amount)
        VALUES (?, ?, ?)
    ''', (payout_date, original_order_date, amount))
    conn.commit()
    conn.close()
    if original_order_date:
        print(f"一笔来自 {original_order_date} 订单的提前回款 {amount:.2f} 元已记录在 {payout_date}。")
    else:
        print(f"一笔来源未知的提前回款 {amount:.2f} 元已记录在 {payout_date}。")

def delete_early_payout_by_id(payout_id):
    """根据唯一的ID删除一条提前回款记录。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"DELETE FROM {EARLY_PAYOUT_TABLE} WHERE payout_id = ?", (payout_id,))
    deleted_rows = c.rowcount
    conn.commit()
    conn.close()
    if deleted_rows > 0:
        print(f"ID为 {payout_id} 的提前回款记录已删除。")
        return True
    else:
        print(f"未找到ID为 {payout_id} 的记录。")
        return False

def load_all_early_payouts():
    """从提前回款表加载所有数据，并确保日期列被正确转换。"""
    if not os.path.exists(DB_FILE): return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(f'SELECT * FROM {EARLY_PAYOUT_TABLE}', conn)
        if not df.empty:
            df['Payout_Date'] = pd.to_datetime(df['Payout_Date'])
            # Original_Order_Date 可能包含None(NaT)，所以要小心处理
            df['Original_Order_Date'] = pd.to_datetime(df['Original_Order_Date'], errors='coerce')
        return df
    except Exception as e:
        print(f"加载提前回款数据失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def delete_data_by_date(date_str):
    """根据日期删除主数据表中的一条数据。(无变化)"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"DELETE FROM {DAILY_TABLE} WHERE Date = ?", (date_str,))
    conn.commit()
    conn.close()
    print(f"日期 {date_str} 的主数据已删除。")

def load_all_data():
    """从主数据表加载所有历史数据到DataFrame。(无变化)"""
    if not os.path.exists(DB_FILE): return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(f'SELECT * FROM {DAILY_TABLE}', conn)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"加载主数据失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def load_all_early_payouts():
    """从提前回款表加载所有数据到DataFrame。(无变化)"""
    if not os.path.exists(DB_FILE): return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(f'SELECT * FROM {EARLY_PAYOUT_TABLE}', conn)
        df['Payout_Date'] = pd.to_datetime(df['Payout_Date'])
        df['Original_Order_Date'] = pd.to_datetime(df['Original_Order_Date'])
        return df
    except Exception as e:
        print(f"加载提前回款数据失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()
