import sqlite3
from datetime import datetime, timedelta
import config
import pandas as pd

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
                
                -- 对账状态机
                reconciliation_status TEXT DEFAULT NULL, -- NULL (不适用), 'UNMATCHED' (待对账), 'MATCHED' (已对账)
                
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


def logPayout(payout_date: str, amount: float, description: str) -> bool:
    """
    (核心事务 B) 录入一笔平台回款
    只录入一笔回款，并将其标记为 "待对账" (UNMATCHED)
    """
    print(f"正在录入一笔待对账回款 (金额: {amount})...")
    conn = None

    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 1. 只插入 'transactions' 表 (记录银行入账)
        c.execute(
            "INSERT INTO transactions (date_posted, amount, type, description, reconciliation_status) VALUES (?, ?, 'PAYOUT', ?, 'UNMATCHED')",
            (payout_date, amount, description)
        )
        conn.commit()
        print(f"回款 ¥{amount} 已入账，状态为 'UNMATCHED'。")
        return True

    except sqlite3.Error as e:
        print(f"录入回款时发生错误: {e}")
        if conn:
            conn.rollback() 
        return False
    finally:
        if conn:
            conn.close()


def CancelOrders(order_id: int, cost_refunded: bool, seller_pays_shipping: bool) -> bool:
    """
    (核心事务 C) 处理一笔订单的取消 (退款)。
    这是一个事务，会：
    1. 将 'orders' 状态设为 'CANCELLED'。
    2. (如果 cost_refunded) 在 'transactions' 加回 "垫付成本"。
    3. (如果 seller_pays_shipping) 在 'transactions' 扣除 "退货运费"。
    """
    print(f"正在取消订单 ID: {order_id} (成本退回: {cost_refunded}, 卖家付运费: {seller_pays_shipping})...")
    conn = None

    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 1. 获取这笔订单的原始垫付成本
        c.execute("SELECT cost_advanced FROM orders WHERE order_id = ?", (order_id,))
        result = c.fetchone()
        if not result:
            print(f"错误：未找到订单 {order_id}。")
            return False
        original_cost = result[0]

        # 2. 开始事务
        c.execute("BEGIN TRANSACTION;") # 显式开启事务

        # 步骤 a: 更新订单状态
        c.execute(
            "UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?",
            (order_id,)
        )

        today_str = datetime.now().strftime('%Y-%m-%d')

        # 步骤 b: (如果) 垫付成本退回
        if cost_refunded:
            c.execute(
                """
                INSERT INTO transactions (date_posted, amount, type, description, related_order_id)
                VALUES (?, ?, 'COST_REFUND', ?, ?)
                """,
                (today_str, original_cost, f"订单 {order_id} 成本退回", order_id)
            )

        # 步骤 c: (如果) 卖家承担退货运费
        if seller_pays_shipping:
            shipping_fee = config.DEFAULT_RETURN_SHIPPING_FEE
            c.execute(
                """
                INSERT INTO transactions (date_posted, amount, type, description, related_order_id)
                VALUES (?, ?, 'RETURN_SHIPPING_FEE', ?, ?)
                """,
                (today_str, -abs(shipping_fee), f"订单 {order_id} 退货运费", order_id)
            )

        # 3. 提交事务
        c.execute("COMMIT;")

        print(f"成功：订单 {order_id} 已取消并处理了相关流水。")
        return True

    except sqlite3.Error as e:
        print(f"V3 取消订单时发生错误: {e}")
        if conn:
            c.execute("ROLLBACK;") # 确保回滚
        return False
    finally:
        if conn:
            conn.close()



# 3. 核心工作流 (读取)
def getCurrentBalance() -> float:     # 函数返回值类型提示（Type Hint）
    """
    (Query 1) 实时计算当前银行余额
    这是 'transactions' 表中所有 'amount' 的总和。
    """
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        c.execute("SELECT SUM(amount) FROM transactions;")
        result = c.fetchone()       # 游标用法，获取上一次SELECT查询结果中的“第一行数据”

        # 如果从未有过交易 (表为空)，fetchone() 会返回 (None,)
        balance = result[0] if result and result[0] is not None else 0.0      # 安全处理查询结果，避免空值错误；提取总和结果，若为 None 则视为 0.0
        return float(balance)
    
    except sqlite3.Error as e:
        print(f"读取银行余额时发生错误: {e}")
        return 0.0 # 发生错误时返回 0，防止应用崩溃
    finally:
        if conn:
            conn.close()


def getAverageOrderCost() -> float:
    """
    (Query 3-sub) 实时计算平均垫付成本
    只计算未被取消的订单。
    """
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 排除 'CANCELLED' 订单，因为它们不代表真实的运营成本
        c.execute("SELECT AVG(cost_advanced) FROM orders WHERE status != 'CANCELLED';")
        result = c.fetchone()

        average_cost = result[0] if result and result[0] is not None else 0.0
        return float(average_cost)
    
    except sqlite3.Error as e:
        print(f"读取平均成本时发生错误: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()


def getFuturePayoutSchedule() -> pd.DataFrame:
    """
    (Query 2) 获取未来待回款日历
    只查询 'PENDING' 状态的订单。
    """
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 这个查询自动忽略了 'PAID' 和 'CANCELLED' 的订单
        query = """
            SELECT 
                expected_payout_date, 
                SUM(cost_advanced + expected_profit) as daily_payout_total
            FROM orders
            WHERE status = 'PENDING'
            GROUP BY expected_payout_date
            ORDER BY expected_payout_date;
        """

        # pd.read_sql_query 是将 SQL 结果直接转为 DataFrame 的最快方式
        df = pd.read_sql_query(query, conn)     # query 定义了 “要获取什么数据”;conn 定义了 “从哪里获取数据”
        return df

    except sqlite3.Error as e:
        print(f"读取未来回款时发生错误: {e}")
        return pd.DataFrame(columns=['expected_payout_date', 'daily_payout_total'])  # 返回空表
    finally:
        if conn:
            conn.close()


def getAallOrdersDF() -> pd.DataFrame:
    """
    获取所有订单记录，用于管理页面显示。
    """
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        # 选择所有列，按创建日期倒序，最新的在最前面
        query = "SELECT * FROM orders ORDER BY date_created DESC, order_id DESC"
        df = pd.read_sql_query(query, conn)      
        return df
    
    except sqlite3.Error as e:
        print(f"读取所有订单时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def getAllTransactionsDF() -> pd.DataFrame:
    """
    获取所有银行流水，用于对账页面显示。
    """
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        query = "SELECT * FROM transactions ORDER BY date_posted DESC, transaction_id DESC"
        df = pd.read_sql_query(query, conn)
        return df
    
    except sqlite3.Error as e:
        print(f"读取所有交易时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def logFixedExpense(name: str, amount: float) -> bool:
    """
    录入一笔固定支出 (非订单)
    这只会影响 'transactions' 表
    """
    print(f"正在录入固定支出: {name}, 金额: {amount}...")
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        today_str = datetime.now().strftime('%Y-%m-%d')     # 获取当前日期字符串

        c.execute(
            """
            INSERT INTO transactions (date_posted, amount, type, description)
            VALUES (?, ?, 'FIXED_EXPENSE', ?)
            """,
            (today_str, -abs(amount), name)   # 金额必须是负数
            # 一笔是成本退回(正向流水)，一笔是运费支出(负向流水)，是两笔独立流水，不混合
        )
        conn.commit()
        print(f"支出 {name} 已成功录入。")
        return True
    except sqlite3.Error as e:
        print(f"录入固定支出时发生错误: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()



# 图表
def getOrdeVolumeHistory() -> pd.DataFrame:
    """
    获取每日订单量历史 (用于图表)
    """
    conn = None

    try:
        conn = _getdbConnect()
        # 按创建日期统计订单数量
        query = """
            SELECT 
                date_created, 
                COUNT(order_id) as daily_order_count
            FROM orders
            GROUP BY date_created
            ORDER BY date_created;
        """
        df = pd.read_sql_query(query, conn)
        # 确保日期列是 datetime 类型，方便 Streamlit 绘图
        df['date_created'] = pd.to_datetime(df['date_created'])
        return df
    except sqlite3.Error as e:
        print(f"读取订单量历史时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()


def getBalanceHistory() -> pd.DataFrame:
    """
    获取银行余额历史 (用于图表)
    (高级SQL ：使用窗口函数)
    """
    conn = None
    try:
        conn = _getdbConnect()
        # SUM(amount) OVER (...) 是 SQL 窗口函数
        # 它会计算 "截止到当前行" 的累计总和
        query = """
            SELECT 
                date_posted,
                transaction_id,
                description,
                amount,
                SUM(amount) OVER (
                    ORDER BY date_posted, transaction_id
                ) as cumulative_balance
            FROM transactions
            ORDER BY date_posted, transaction_id;
        """
        df = pd.read_sql_query(query, conn)
        df['date_posted'] = pd.to_datetime(df['date_posted'])
        return df
    except sqlite3.Error as e:
        print(f"读取余额历史时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()



def getUnmatchedPayouts() -> pd.DataFrame:
    """获取所有 '待对账' (UNMATCHED) 的回款"""
    conn = None
    try:
        conn = _getdbConnect()
        query = "SELECT * FROM transactions WHERE type = 'PAYOUT' AND reconciliation_status = 'UNMATCHED' ORDER BY date_posted DESC"
        df = pd.read_sql_query(query, conn)
        return df
    except sqlite3.Error as e:
        print(f"读取待对账回款时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()


def getReconcilableOrders() -> pd.DataFrame:
    """获取所有 '待回款' (PENDING) 的订单"""
    conn = None
    try:
        conn = _getdbConnect()
        query = "SELECT order_id, date_created, cost_advanced, expected_profit, (cost_advanced + expected_profit) as expected_payout FROM orders WHERE status = 'PENDING' ORDER BY date_created"
        df = pd.read_sql_query(query, conn)
        return df
    except sqlite3.Error as e:
        print(f"读取待回款订单时发生错误: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()


def ReconcilePayoutToOrders(payout_transaction_id: int, order_ids_list: list) -> bool:
    """
    执行对账
    将一笔 'PAYOUT' 标记为 'MATCHED'，并将其关联的 'PENDING' 订单标记为 'PAID'。
    """
    if not order_ids_list:
        print("错误：对账必须至少选择一笔订单。")
        return False

    print(f"正在执行对账：将回款 {payout_transaction_id} 关联到 {len(order_ids_list)} 笔订单...")
    conn = None
    try:
        conn = _getdbConnect()
        c = conn.cursor()

        c.execute("BEGIN TRANSACTION;") # 显式开启事务

        # 1. 标记 'transactions' 表（指更新表中记录的状态或关联信息）
        c.execute(
            "UPDATE transactions SET reconciliation_status = 'MATCHED' WHERE transaction_id = ?",
            (payout_transaction_id,)
        )

        # 2. 标记 'orders' 表
        #    (这里用了一个小技巧， '?' 占位符列表必须是元组列表)
        params = []
        for order_id in order_ids_list:
            params.append((payout_transaction_id, order_id))    # (new_payout_id, order_id_to_update)

        # executemany 批量更新
        c.executemany(
            """
            UPDATE orders 
            SET status = 'PAID', payout_transaction_id = ?
            WHERE order_id = ? AND status = 'PENDING'
            """,
            params
        )

        c.execute("COMMIT;")
        print("成功：对账事务已提交。")
        return True

    except sqlite3.Error as e:
        print(f"V3 对账事务发生错误: {e}")
        if conn:
            c.execute("ROLLBACK;")
        return False
    finally:
        if conn: conn.close()