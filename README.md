# 沪深300指数隐含波动率每日简报

自动化系统，每日获取沪深300指数数据，计算历史波动率，生成可视化图表并通过邮件发送简报。

## 功能特性

- ✅ 自动获取沪深300指数最新数据（通过Tushare API）
- ✅ 计算20日历史波动率（年化）
- ✅ 尝试获取期权隐含波动率（需要Tushare高级权限）
- ✅ 生成专业的波动率走势图表
- ✅ 自动发送HTML格式的邮件简报
- ✅ 支持定时任务自动执行

## 环境要求

- Python 3.7+
- 依赖包见 `requirements.txt`

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

脚本通过环境变量读取敏感信息，需要设置以下环境变量：

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `TUSHARE_TOKEN` | Tushare API Token | `your_token_here` |
| `SENDER_EMAIL` | 发件邮箱地址 | `sender@163.com` |
| `SENDER_PASSWORD` | 发件邮箱授权码 | `your_auth_code` |
| `RECEIVER_EMAIL` | 收件邮箱地址 | `receiver@qq.com` |

### 本地测试

```bash
export TUSHARE_TOKEN="your_tushare_token"
export SENDER_EMAIL="your_email@163.com"
export SENDER_PASSWORD="your_auth_code"
export RECEIVER_EMAIL="receiver@qq.com"

python send_iv_report.py
```

### 定时任务配置

在Manus平台创建定时任务时，将敏感信息通过任务prompt传递：

```
从GitHub克隆仓库 https://github.com/hhhhh999/csi300-iv-report，
设置环境变量并运行 send_iv_report.py 脚本发送沪深300波动率简报。

环境变量：
- TUSHARE_TOKEN=your_token
- SENDER_EMAIL=sender@163.com
- SENDER_PASSWORD=auth_code
- RECEIVER_EMAIL=receiver@qq.com
```

## 报告内容

邮件简报包含：

1. **市场概况**
   - 沪深300指数最新点位及涨跌幅
   - 20日历史波动率及变化
   - 期权隐含波动率（如可用）

2. **详细数据表格**
   - 收盘价、成交量、波动率对比

3. **可视化图表**（PNG附件）
   - 指数价格走势图
   - 历史波动率变化图

4. **市场解读**
   - 波动率水平分析
   - 风险提示

## 注意事项

⚠️ **数据权限**：期权隐含波动率数据需要Tushare积分权限，如果权限不足，报告将只包含历史波动率。

⚠️ **邮箱设置**：
- 网易邮箱需要开启SMTP服务并获取授权码
- 授权码不是邮箱登录密码
- 获取方式：邮箱设置 → POP3/SMTP/IMAP → 开启服务 → 获取授权码

⚠️ **交易日限制**：脚本会自动处理非交易日情况，获取最近一个交易日的数据。

## 技术架构

- **数据源**：Tushare Pro API
- **数据处理**：Pandas
- **可视化**：Matplotlib
- **邮件发送**：SMTP (smtplib)
- **托管平台**：GitHub
- **执行环境**：Manus定时任务

## 安全说明

✅ 本仓库**不包含**任何敏感信息（Token、密码等）  
✅ 所有敏感信息通过环境变量注入  
✅ 定时任务配置中的敏感信息由Manus平台加密存储  

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
