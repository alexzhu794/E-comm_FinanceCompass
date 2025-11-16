'''
职责:
1. 协调 data_manager.py (Hands)。
2. 执行业务计算 (如 "余额 / 成本")。
3. 为 app.py (UI) 提供简单、干净的函数。
4. (重要) 此文件不应包含任何 SQL 语句。
'''

import data_manager
import math

# 1. 仪表盘 "读取" 逻辑
def getDdashboardMetrics() -> dict:
    '''
    获取仪表盘所需的所有核心指标
    返回一个包含关键财务指标的字典
    '''

    # 调用：从 data_manager 获取原始数据
    current_balance = data_manager.getCurrentBalance()
    avg_cost = data_manager.getAverageOrderCost()

    # 执行：业务计算
    safe_orders_today = 0
    if avg_cost > 0:
        # 使用 math.floor() 向下取整，因为我们不能垫付 0.8 单
        safe_orders_today = math.floor(current_balance / avg_cost)

    # 返回：将所有计算结果打包成一个字典，供 UI 使用
    metrics = {
        "current_balance": current_balance,     # 实时银行余额 (Query 1)
        "avg_cost_per_order": avg_cost,     # 平均垫付成本 (Query 3-sub)
        "safe_orders_today": safe_orders_today  # "安全接单数" (Query 3)
    }
    return metrics

def getPayoutChartData():
    """
    获取未来回款图表所需的数据。
    (这个函数目前只是一个简单的传递，未来可以增加更复杂的预测逻辑)
    """
    print("Logic Driver: 正在获取回款图表数据...")
    return data_manager.getFuturePayoutSchedule()

def getAllOrders():
    """获取所有订单，用于管理页面"""
    print("Logic Driver: G正在获取所有订单...")
    return data_manager.getAallOrdersDF()

def getAllTransactions():
    """获取所有交易，用于对账页面"""
    print("Logic Driver: 正在获取所有交易...")
    return data_manager.getAllTransactionsDF()


# 2. 录入 "写入" 逻辑 (封装)
'''
这些函数是 "封装器" (Wrappers)，它们将 UI 的请求传递给 data_manager.py
这样做的好处是：
UI (app.py) 只与 "大脑" (logic_driver.py) 对话
# "大脑" 再去命令 "双手" (data_manager.py) 执行
# 这保证了 UI 和数据库的完全解耦。
'''

def HandleInitialCapital(amount: float) -> bool:
    """封装：录入启动资金"""
    print(f"Logic Driver: 正在处理启动资金 {amount}元...")
    # (目前没有业务逻辑，直接传递)
    return data_manager.logInitCapital(amount)


def HandleNewOrder(cost: float, profit: float) -> bool:
    """封装：录入新订单"""
    print(f"Logic Driver: 正在处理新订单 (成本: {cost}, 利润: {profit})...")

    # 业务逻辑检查：不允许成本或利润为负
    if cost < 0 or profit < 0:
        print("错误：成本或利润不能为负数。")
        return False
        
    return data_manager.CreateNewOrder(cost, profit)


def HandlePayout(payout_date: str, original_order_date: str, amount: float) -> bool:
    """封装：录入平台回款"""
    print(f"Logic Driver: 正在处理回款 (金额: {amount})...")
    
    # 业务逻辑检查
    if amount <= 0:
        print("错误：回款金额必须大于0。")
        return False
        
    return data_manager.logPayout(payout_date, original_order_date, amount)


def HandleCancelOrder(order_id: int) -> bool:
    """封装：取消订单"""
    print(f"Logic Driver: 正在处理取消订单 (ID: {order_id})...")
    
    # 业务逻辑检查
    if order_id <= 0:
        print("错误：订单 ID 无效。")
        return False
        
    return data_manager.CancelOrders(order_id)