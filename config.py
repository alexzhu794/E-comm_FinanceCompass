# --- 数据库配置 ---
DB_FILE = 'finance_guardian.db'   # SQLite 数据库文件的名称

# --- 业务逻辑配置 ---
# 平台回款周期 (单位：天)
PAYOUT_DELAY_DAYS = 15     # 15天意味着 11月1日 的订单，将在 11月16日 回款