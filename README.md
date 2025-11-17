# 现金流守护者 (Cash Flow Guardian) 

这是一个基于 Streamlit 和 SQLite 事务的现金流模拟器，专为解决小型电商商家（尤其是“一件代发”模式）的核心痛点：**因平台账期导致的现金流断裂**。

本项目 (V3) 是对一个早期原型 (V1) 的彻底重构，旨在解决 V1 在性能、数据保真度和算法鲁棒性上的所有根本性缺陷。

## V1 -\> V3: 架构重构

V1 是一个脆弱的计算器，V3 是一个健壮的事务性账本。这次重构解决了 V1 的所有核心问题：

| V1 缺陷 | V3 解决方案 (架构级) |
| :--- | :--- |
| **性能灾难**: `O(N)` 全局重算。 | **`O(1)` 增量计算**: 采用“写入时计算”，`transactions` 表 存储原子事件，余额 `SUM()` 出来，性能瞬时。 |
| **数据保真度丢失**: 存储“每日汇总”，丢弃单笔订单。 | **事件溯源 (Event-Sourcing)**: `orders` 和 `transactions` 表记录每一笔不可变的“事实”。 |
| **算法脆弱**: `900.0` 魔术数字，简单 `mean()` 易被污染。 | **动态推导**: 平均成本 `AVG(cost_advanced)` 动态计算，预测更健壮。 |
| **业务逻辑僵化**: 无法处理批量回款、提前回款。 | **人工对账 (V3)**: 引入 `'UNMATCHED'` 状态 和对账页面，完美解决真实世界难题。 |
| **业务闭环缺失**: 无法处理退款、固定支出。 | **高级事务 (V3)**: 引入高级退款 (含运费) 和固定支出 流水，实现财务闭环。 |

## V3 架构与核心设计

V3 采用了清晰的三层架构：

  * **`app.py` (UI / 展示层)**：只负责“画”页面，只与“大脑”对话。
  * **`logic_driver.py` (业务层 / 大脑)**：负责业务计算、封装、协调，只与“双手”对话。
  * **`data_manager.py` (数据层 / 双手)**：包含所有 SQL 查询和事务，是唯一能碰数据库的组件。

### 数据库设计 (The "Core")

我使用两张规范化的表来构建一个“复式记账”系统：

1.  **`transactions` (银行流水表)**

      * **职责**：唯一的“资金真相”。
      * **设计**：记录**每一笔**资金变动（`amount` 正为入，负为出）。
      * **`type`**：`INITIAL_CAPITAL`, `ORDER_COST` (垫付成本), `PAYOUT` (回款), `COST_REFUND` (成本退回), `FIXED_EXPENSE` (固定支出)...
      * **`reconciliation_status` (V3)**: `'UNMATCHED'` (待对账), `'MATCHED'` (已对账)。

2.  **`orders` (订单状态表)**

      * **职责**：“业务事实”的状态机。
      * **`status` (核心)**：`PENDING`, `PAID`, `CANCELLED`。
      * **外键**：通过 `payout_trans_id` 和 `related_order_id` 将两张表关联。
---

## 功能亮点 (Showcase)

### 1\. 原子事务 (Atomicity)

V3 的所有“写入”操作都封装在 `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK` 中，展示了对数据完整性的掌控。

  * **`CreateNewOrder`**：原子化地 `INSERT INTO orders` (创单) 和 `INSERT INTO transactions` (扣款)，杜绝“幽灵数据”。
  * **`CancelOrders` (V3)**：原子化地 `UPDATE orders` (改状态)，并根据逻辑 `INSERT` 成本退回 `COST_REFUND` 和运费支出 `RETURN_SHIPPING_FEE`。

### 2\. 人工财务对账 (Reconciliation)

V3 解决了 V1 无法处理的 **“批量回款”** 和 **“提前回款”** 的难题。

1.  `logPayout` 只负责记录“银行入账”，并标记为 `'UNMATCHED'`。
2.  "财务对账" 页面 允许用户**手动勾选**“哪笔回款 (`transactions`)” 对应“哪些订单 (`orders`)”。
3.  `ReconcilePayoutToOrders` 事务在后台执行，将 `orders.status` 更新为 `PAID`，并将 `transactions.status` 更新为 `MATCHED`，完成闭环。

### 3\. 高级 SQL (Window Functions)

V3 的“余额历史图” 功能运用了高级 SQL（窗口函数）。我们不使用缓慢的 Python 循环，而是直接在数据库中计算累计和。

---
## 技术栈 (Tech Stack)

  * **UI / Web 框架**: Streamlit
  * **后端逻辑**: Python
  * **数据库**: SQLite (通过 `sqlite3` 库进行事务控制)
  * **数据操作**: Pandas (用于 `st.dataframe` 和图表)
  * **配置管理**: `config.py`

## 如何运行 (How to Run)

1.  **克隆仓库**

    ```bash
    git clone [你的 GITHUB 仓库 URL]
    cd [项目文件夹]
    ```

2.  **创建并激活虚拟环境**

    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS / Linux
    .\venv\Scripts\activate   # Windows
    ```

3.  **安装依赖**

    ```bash
    # requirements.txt 应包含:
    # streamlit
    # pandas

    pip install -r requirements.txt
    ```

4.  **运行应用**

    ```bash
    streamlit run app.py
    ```

5.  **(V3 首次运行)**

      * 应用启动时会自动在本地创建 `finance_guardian.db` 数据库文件。
      * 请先在 "◼️ 录入数据" -\> "录入启动资金" 页面为你自己注入第一笔钱。

