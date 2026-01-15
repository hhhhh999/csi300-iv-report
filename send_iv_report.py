#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300指数隐含波动率每日简报
自动获取数据、生成图表并发送邮件报告
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class CSI300IVReport:
    """沪深300隐含波动率报告生成器"""
    
    def __init__(self, tushare_token):
        """初始化"""
        self.token = tushare_token
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        self.report_date = datetime.now().strftime('%Y-%m-%d')
        
    def get_index_data(self, days=30):
        """获取沪深300指数数据"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 获取沪深300指数日线数据
            df = self.pro.index_daily(
                ts_code='000300.SH',
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                print("警告：未获取到指数数据")
                return None
                
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            
            # 计算历史波动率（20日）
            df['returns'] = df['close'].pct_change()
            df['hist_vol'] = df['returns'].rolling(window=20).std() * (252 ** 0.5) * 100
            
            return df
            
        except Exception as e:
            print(f"获取指数数据失败: {e}")
            return None
    
    def get_option_iv(self):
        """获取期权隐含波动率数据"""
        try:
            # 获取最近的交易日
            trade_date = datetime.now().strftime('%Y%m%d')
            
            # 获取沪深300ETF期权数据（510300.SH）
            # 注意：Tushare的期权数据可能需要更高权限
            df = self.pro.opt_daily(
                exchange='SSE',
                trade_date=trade_date
            )
            
            if df.empty:
                # 如果当天没有数据，尝试前一个交易日
                trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df = self.pro.opt_daily(
                    exchange='SSE',
                    trade_date=trade_date
                )
            
            # 筛选沪深300相关期权
            if not df.empty:
                df_300 = df[df['ts_code'].str.contains('510300')]
                if not df_300.empty:
                    # 计算平均隐含波动率
                    avg_iv = df_300['implied_volatility'].mean() if 'implied_volatility' in df_300.columns else None
                    return avg_iv, trade_date
            
            return None, trade_date
            
        except Exception as e:
            print(f"获取期权IV数据失败: {e}")
            return None, None
    
    def create_volatility_chart(self, df):
        """创建波动率走势图"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 图1: 指数价格走势
            ax1.plot(df['trade_date'], df['close'], 'b-', linewidth=2, label='沪深300指数')
            ax1.set_title('沪深300指数走势', fontsize=14, fontweight='bold')
            ax1.set_ylabel('指数点位', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # 图2: 历史波动率
            ax2.plot(df['trade_date'], df['hist_vol'], 'r-', linewidth=2, label='20日历史波动率')
            ax2.set_title('沪深300历史波动率 (年化%)', fontsize=14, fontweight='bold')
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylabel('波动率 (%)', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存到内存
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            print(f"创建图表失败: {e}")
            return None
    
    def generate_report_content(self, df, option_iv=None):
        """生成报告文本内容"""
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 计算变化
            price_change = latest['close'] - prev['close']
            price_change_pct = (price_change / prev['close']) * 100
            vol_change = latest['hist_vol'] - prev['hist_vol']
            
            # 生成报告
            content = f"""
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, "Microsoft YaHei", sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .metric {{ background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .metric-title {{ font-weight: bold; color: #2c3e50; font-size: 14px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .footer {{ margin-top: 30px; padding: 15px; background-color: #ecf0f1; text-align: center; font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: left; }}
        th {{ background-color: #34495e; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>沪深300指数隐含波动率简报</h1>
        <p>报告日期: {self.report_date}</p>
    </div>
    
    <div class="content">
        <h2>📊 市场概况</h2>
        
        <div class="metric">
            <div class="metric-title">沪深300指数</div>
            <div class="metric-value">{latest['close']:.2f} 
                <span class="{'positive' if price_change >= 0 else 'negative'}">
                    {'+' if price_change >= 0 else ''}{price_change:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                </span>
            </div>
        </div>
        
        <div class="metric">
            <div class="metric-title">20日历史波动率 (年化)</div>
            <div class="metric-value">{latest['hist_vol']:.2f}% 
                <span class="{'positive' if vol_change >= 0 else 'negative'}">
                    {'+' if vol_change >= 0 else ''}{vol_change:.2f}%
                </span>
            </div>
        </div>
        
        {f'''<div class="metric">
            <div class="metric-title">期权隐含波动率</div>
            <div class="metric-value">{option_iv:.2f}%</div>
        </div>''' if option_iv else ''}
        
        <h2>📈 详细数据</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>当前值</th>
                <th>前一日</th>
                <th>变化</th>
            </tr>
            <tr>
                <td>收盘价</td>
                <td>{latest['close']:.2f}</td>
                <td>{prev['close']:.2f}</td>
                <td class="{'positive' if price_change >= 0 else 'negative'}">{'+' if price_change >= 0 else ''}{price_change:.2f}</td>
            </tr>
            <tr>
                <td>成交量 (万手)</td>
                <td>{latest['vol']/10000:.2f}</td>
                <td>{prev['vol']/10000:.2f}</td>
                <td>{(latest['vol']-prev['vol'])/10000:.2f}</td>
            </tr>
            <tr>
                <td>历史波动率</td>
                <td>{latest['hist_vol']:.2f}%</td>
                <td>{prev['hist_vol']:.2f}%</td>
                <td class="{'positive' if vol_change >= 0 else 'negative'}">{'+' if vol_change >= 0 else ''}{vol_change:.2f}%</td>
            </tr>
        </table>
        
        <h2>💡 市场解读</h2>
        <p>
            {'市场波动率上升，建议关注风险管理。' if vol_change > 0 else '市场波动率下降，市场情绪相对稳定。'}
            当前20日历史波动率为 {latest['hist_vol']:.2f}%，
            {'处于较高水平' if latest['hist_vol'] > 20 else '处于正常水平' if latest['hist_vol'] > 15 else '处于较低水平'}。
        </p>
        
        <p><strong>图表说明：</strong>附件中包含沪深300指数走势及波动率变化图表，请查看附件了解详细趋势。</p>
    </div>
    
    <div class="footer">
        <p>本报告由自动化系统生成 | 数据来源: Tushare</p>
        <p>仅供参考，不构成投资建议</p>
    </div>
</body>
</html>
"""
            return content
            
        except Exception as e:
            print(f"生成报告内容失败: {e}")
            return None
    
    def send_email(self, sender_email, sender_password, receiver_email, subject, html_content, chart_buffer):
        """发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart('related')
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # 添加HTML内容
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg_alternative.attach(html_part)
            
            # 添加图表附件
            if chart_buffer:
                chart_buffer.seek(0)
                img = MIMEImage(chart_buffer.read())
                img.add_header('Content-Disposition', 'attachment', filename='volatility_chart.png')
                msg.attach(img)
            
            # 连接SMTP服务器并发送
            print(f"   正在连接 SMTP 服务器 smtp.163.com:465...")
            server = smtplib.SMTP_SSL('smtp.163.com', 465, timeout=30)
            server.set_debuglevel(0)  # 设置为1可查看详细调试信息
            
            print(f"   正在登录邮箱 {sender_email}...")
            server.login(sender_email, sender_password)
            
            print(f"   正在发送邮件到 {receiver_email}...")
            server.send_message(msg)
            server.quit()
            
            print(f"✓ 邮件发送成功: {receiver_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"✗ 邮件认证失败: {e}")
            print("   提示：请检查邮箱授权码是否正确，或重新获取授权码")
            print("   网易邮箱授权码获取：邮箱设置 → POP3/SMTP/IMAP → 授权码管理")
            return False
        except smtplib.SMTPException as e:
            print(f"✗ SMTP错误: {e}")
            return False
        except Exception as e:
            print(f"✗ 邮件发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self, sender_email, sender_password, receiver_email):
        """执行完整流程"""
        print(f"开始生成沪深300波动率简报 - {self.report_date}")
        print("=" * 60)
        
        # 1. 获取数据
        print("1. 获取指数数据...")
        df = self.get_index_data(days=60)
        if df is None or df.empty:
            print("✗ 数据获取失败，无法生成报告")
            return False
        print(f"✓ 成功获取 {len(df)} 条数据")
        
        # 2. 获取期权IV（可选）
        print("2. 获取期权隐含波动率...")
        option_iv, trade_date = self.get_option_iv()
        if option_iv:
            print(f"✓ 期权IV: {option_iv:.2f}%")
        else:
            print("⚠ 期权IV数据不可用（可能需要更高权限）")
        
        # 3. 生成图表
        print("3. 生成波动率图表...")
        chart_buffer = self.create_volatility_chart(df)
        if chart_buffer:
            print("✓ 图表生成成功")
        else:
            print("⚠ 图表生成失败")
        
        # 4. 生成报告内容
        print("4. 生成报告内容...")
        html_content = self.generate_report_content(df, option_iv)
        if html_content:
            print("✓ 报告内容生成成功")
        else:
            print("✗ 报告内容生成失败")
            return False
        
        # 5. 发送邮件
        print("5. 发送邮件...")
        subject = f"沪深300波动率简报 - {self.report_date}"
        success = self.send_email(
            sender_email, 
            sender_password, 
            receiver_email, 
            subject, 
            html_content, 
            chart_buffer
        )
        
        print("=" * 60)
        if success:
            print("✓ 简报发送完成！")
            return True
        else:
            print("✗ 简报发送失败")
            return False


def main():
    """主函数"""
    # 从环境变量读取配置
    tushare_token = os.getenv('TUSHARE_TOKEN')
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    
    # 检查必要参数
    if not all([tushare_token, sender_email, sender_password, receiver_email]):
        print("错误：缺少必要的环境变量")
        print("需要设置: TUSHARE_TOKEN, SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL")
        sys.exit(1)
    
    # 创建报告生成器并运行
    reporter = CSI300IVReport(tushare_token)
    success = reporter.run(sender_email, sender_password, receiver_email)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
