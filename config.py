# 数据库配置
DB_FILE = 'finance_guardian.db'   # SQLite 数据库文件的名称

# 业务逻辑配置
# 平台回款周期 (单位：天)
PAYOUT_DELAY_DAYS = 15     # 15天意味着 11月1日 的订单，将在 11月16日 回款

# 固定支出模板
# 格式: {'name': '支出名称', 'default_amount': 默认金额}
RECURRING_EXPENSE_TEMPLATES = [
    {'name': '云仓月费', 'default_amount': 300.00},
    {'name': 'SaaS 软件订阅', 'default_amount': 50.00},
    {'name': '广告投放', 'default_amount': 100.00},
    {'name': '自定义支出', 'default_amount': 0.00},
]


# 退款运费配置
# 卖家承担的默认退货运费
DEFAULT_RETURN_SHIPPING_FEE = 8.00