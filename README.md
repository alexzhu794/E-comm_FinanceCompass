# 🧭 E-commerce 财务罗盘 (E-commerce Finance Compass)

一个基于Python和Streamlit构建的、交互式的电商财务智能分析与增长建议助手。

---

## ✨ 核心功能 (Core Features)

- **多模式数据录入**: 支持**逐单精细录入**（记录每单的成本与利润）和**每日汇总快速录入**，满足不同场景下的记账需求。
- **全自动财务计算**: 实时计算每日运营成本、利润、净现金流和银行余额，自动处理15天的资金回款周期。
- **灵活的财务事件处理**:
    - **提前回款**: 支持记录来源明确或未知的提前回款，并能精确处理其对现金流和未来应收款的影响。
    - **退款处理**: 能根据退款金额，按预设的平均利润率估算利润损失，并从累计利润中冲销，确保利润数据的真实性。
- **智能增长预测**: 基于稳定运营期的现金流数据，动态预测下一个安全的**增单时间点**和所需缓冲资金，为业务增长提供数据驱动的建议。
- **交互式数据可视化**: 在Web界面上直接展示银行余额、每日净现金流、累计利润的动态趋势图表，让财务状况一目了然。
- **完整的Web化数据管理**: 提供安全、友好的图形化界面，用于新增、查看、**删除**每日主数据及提前回款记录，彻底告别命令行。

---

## 🛠️ 技术栈 (Tech Stack)

- **核心语言**: Python
- **Web框架 / UI**: Streamlit
- **数据处理**: Pandas
- **数据存储**: SQLite
- **可视化**: Matplotlib



---

## 📖 使用指南 (Usage)

应用启动后，通过左侧的侧边栏进行导航：

- **仪表盘 & 报告**: 查看最新的财务快照、增长预测以及所有财务趋势图表。
- **✍️ 录入**: 选择“精细”或“快速”模式，录入当天的订单、退款及其他收入。
- **📈 管理提前回款**: 看或删除提前到账的回款记录。
- **🗑️ 删除每日数据**: 安全地删除某个特定日期的所有主数据记录


## 📄 开源许可证 (License)

本项目采用 [MIT License](LICENSE) 开源许可证。

