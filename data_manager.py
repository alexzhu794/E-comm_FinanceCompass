import sqlite3
from datetime import datetime, timedelta
import config

def _getdbConnect():
    """获取一个数据库连接，并启用外键约束"""
    conn = sqlite3.connect(DB_FILE)    

    # SQLite 默认不开启外键约束，必须手动开启
    conn.execute("PRAGMA foreign_keys = ON;")   # 等同于conn.cursor().execute(...)
    return conn


# 1. 数据库初始化
def init_db():
    ''' 初始化数据库，创建核心的 'orders' 和 'transactions' 表 '''
    print("正在初始化数据库...")
    conn = None    # 确保后续 finally 块中 if conn: 的判断始终有效

    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 订单表 (Orders Table) - 记录所有已承诺的订单
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders(
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_created TEXT NOT NULL,          -- 订单创建日期 (YYYY-MM-DD)
                cost_advanced REAL NOT NULL,         -- 垫付成本
                expected_profit REAL NOT NULL,       -- 预期利润
                expected_payout_date TEXT NOT NULL,  -- 预期回款日

                -- 核状态机
                status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING (待回款), PAID (已回款), CANCELLED (已退款)

                -- 外键: 用于关联 "哪笔回款" 结清了 "这笔订单"
                payout_trans_id INTEGER,
                FOREIGN KEY (payout_trans_id) REFERENCES transactions(transaction_id)
            )
        ''')

        # 银行流水表 (Transactions Table)
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions(
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_posted TEXT NOT NULL,           -- 资金变动日期
                amount REAL NOT NULL,                -- 变动金额 (正数为入, 负数为出)
                
                -- 资金变动的原因
                type TEXT NOT NULL,  -- 'INITIAL_CAPITAL', 'ORDER_COST', 'PAYOUT', 'REFUND_FEE', 'OTHER_INCOME'
                
                description TEXT,
                
                -- 外键：用于关联 "这笔资金" 是由 "哪笔订单" 引起的
                related_order_id INTEGER,
                FOREIGN KEY (related_order_id) REFERENCES orders(order_id)
            )
        ''')

        conn.commit()
        print(f"数据库 '{DB_FILE}' 已成功初始化。 'orders' 和 'transactions' 表已准备就绪。")

    except sqlite3.Error as e:
        print(f"数据库初始化时发生错误: {e}")

    finally:
        if conn:
            conn.close()


# 2. 核心工作流 (写入)
def logInitCapital(amount:float):
    '''记录启动资金'''
    if amount <= 0:
        print("启动资金必须大于0")
        return                             # 无显式返回值，实际返回 None

    print(f"正在录入启动资金: {amount}元...")
    conn = None

    try:
        conn = _getdbConnect()
        c = conn.cursor()

        today_str = datetime.now().strftime('%Y-%m-%d')   # 获取当前的系统日期

        c.execute(
            "INSERT INTO transactions (date_posted, amount, type, description) VALUES (?, ?, ?, ?)",
            (today_str, amount, 'INITIAL_CAPITAL', '初始启动资金')    # 参数列表，按顺序对应替换4个？占位符
        )

        conn.commit()
        print("启动资金已成功录入。")
    
    except sqlite3.Error as e:
        print(f"录入启动资金时发生错误: {e}")
        if conn:
            conn.rollback()  # 回滚事务
    finally:
        if conn:
            conn.close()


def CreateNewOrder(cost: float, profit: float):
    """
    (核心事务 A) 录入一笔新订单。
    这必须是一个原子事务：
    1. 在 'orders' 表创建 'PENDING' 记录。
    2. 在 'transactions' 表创建 'ORDER_COST' 支出记录。
    必须同时成功，或同时失败。
    """
    print(f"正在处理新订单 (成本: {cost}, 利润: {profit})...")
    conn = None

    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 准备数据
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        payout_date = (today + timedelta(days=PAYOUT_DELAY_DAYS)).strftime('%Y-%m-%d')   # timedelta时间间隔类用于计算时间差值
        cost_advanced = abs(cost)  # 确保成本是正数
        amount_out = -cost_advanced  # 交易金额是负数 (支出)

        # 开始 SQL 事务
        # 1. 插入 'orders' 表
        c.execute(
            "INSERT INTO orders (date_created, cost_advanced, expected_profit, expected_payout_date, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (today_str, cost_advanced, profit, payout_date)
        )

        new_order_id = c.lastrowid   # 获取刚刚插入的那条新订单的order_id，用于外键关联; 与orders表里的order_id字段是同一个值，只是这里为它专门做了单独标识
                                     # c.lastrowid是SQLite3游标cursor的一个属性，专门用于获取“最近一次执行INSERT语句时生成的自增主键值”

        # 2. 插入 'transactions' 表
        c.execute(
            "INSERT INTO transactions (date_posted, amount, type, description, related_order_id) VALUES (?, ?, 'ORDER_COST', ?, ?)",
            (today_str, amount_out, f"垫付订单 {new_order_id} 成本", new_order_id)
        )

        conn.commit()
        print(f"成功：订单 {new_order_id} 已创建，成本 {amount_out} 已从银行扣除。")
        return True       # 表示逻辑执行成功

    except sqlite3.Error as e:
        print(f"创建新订单时发生错误: {e}")
        if conn:
            conn.rollback()
        return False      # 表示逻辑执行失败

    finally:
        if conn:
            conn.close()
