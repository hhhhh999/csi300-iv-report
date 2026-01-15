#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300指数隐含波动率每日简报 V2
支持多种IV数据源，自动降级策略
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class CSI300IVReport:
    """沪深300隐含波动率报告生成器"""
    
    def __init__(self, tushare_token):
        """初始化"""
        self.token = tushare_token
        self.report_date = datetime.now().strftime('%Y-%m-%d')
        self.iv_data = {}  # 存储各种IV数据
        
    def get_index_data(self, days=60):
        """获取沪深300指数数据"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            pro = ts.pro_api()
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 获取沪深300指数日线数据
            df = pro.index_daily(
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
    
    def get_iv_method1_qvix(self):
        """方法1: 获取中证300波动率指数 QVIX"""
        try:
            import akshare as ak
            
            print("  尝试方法1: AkShare QVIX指数...")
            df = ak.index_option_300index_qvix()
            
            if not df.empty:
                latest = df.iloc[-1]
                iv_value = latest['close']
                trade_date = latest['date']
                
                print(f"  ✓ QVIX指数: {iv_value:.2f} ({trade_date})")
                return {
                    'value': iv_value,
                    'date': trade_date,
                    'source': 'QVIX指数',
                    'method': '中证300股指期权波动率指数'
                }
        except Exception as e:
            print(f"  ✗ QVIX获取失败: {str(e)[:50]}")
        
        return None
    
    def get_iv_method2_tushare_vix(self):
        """方法2: 获取Tushare中证波动率指数"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            pro = ts.pro_api()
            
            print("  尝试方法2: Tushare波动率指数(000188.SH)...")
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            
            df = pro.index_daily(
                ts_code='000188.SH',
                start_date=start_date,
                end_date=end_date
            )
            
            if not df.empty:
                df = df.sort_values('trade_date')
                latest = df.iloc[-1]
                iv_value = latest['close']
                trade_date = latest['trade_date']
                
                print(f"  ✓ 中证波动率指数: {iv_value:.2f} ({trade_date})")
                return {
                    'value': iv_value,
                    'date': trade_date,
                    'source': '中证波动率指数',
                    'method': 'Tushare 000188.SH'
                }
        except Exception as e:
            print(f"  ✗ 中证波动率指数获取失败: {str(e)[:50]}")
        
        return None
    
    def get_iv_method3_hist_vol(self, df_index):
        """方法3: 使用历史波动率作为IV近似"""
        try:
            if df_index is None or df_index.empty:
                return None
            
            print("  尝试方法3: 历史波动率(20日年化)...")
            
            latest = df_index.iloc[-1]
            iv_value = latest['hist_vol']
            trade_date = latest['trade_date'].strftime('%Y%m%d')
            
            print(f"  ✓ 历史波动率: {iv_value:.2f}% ({trade_date})")
            return {
                'value': iv_value,
                'date': trade_date,
                'source': '历史波动率',
                'method': '20日滚动年化标准差'
            }
        except Exception as e:
            print(f"  ✗ 历史波动率计算失败: {e}")
        
        return None
    
    def get_implied_volatility(self, df_index=None):
        """获取隐含波动率（多种方法，自动降级）"""
        print("正在获取隐含波动率...")
        
        # 方法1: QVIX指数
        iv_data = self.get_iv_method1_qvix()
        if iv_data:
            self.iv_data = iv_data
            return iv_data['value'], iv_data['source']
        
        # 方法2: Tushare波动率指数
        iv_data = self.get_iv_method2_tushare_vix()
        if iv_data:
            self.iv_data = iv_data
            return iv_data['value'], iv_data['source']
        
        # 方法3: 历史波动率
        iv_data = self.get_iv_method3_hist_vol(df_index)
        if iv_data:
            self.iv_data = iv_data
            return iv_data['value'], iv_data['source']
        
        print("  ✗ 所有IV获取方法均失败")
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
    
    def generate_report_content(self, df):
        """生成报告文本内容"""
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 计算变化
            price_change = latest['close'] - prev['close']
            price_change_pct = (price_change / prev['close']) * 100
            vol_change = latest['hist_vol'] - prev['hist_vol']
            
            # IV信息
            iv_section = ""
            if self.iv_data:
                iv_value = self.iv_data['value']
                iv_source = self.iv_data['source']
                iv_method = self.iv_data['method']
                
                iv_section = f'''
        <div class="metric">
            <div class="metric-title">隐含波动率 (IV)</div>
            <div class="metric-value">{iv_value:.2f}%</div>
            <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                数据来源: {iv_source}<br>
                计算方法: {iv_method}
            </div>
        </div>
        '''
            
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
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; margin-top: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .footer {{ margin-top: 30px; padding: 15px; background-color: #ecf0f1; text-align: center; font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: left; }}
        th {{ background-color: #34495e; color: white; }}
        .info-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 沪深300指数隐含波动率简报</h1>
        <p>报告日期: {self.report_date}</p>
    </div>
    
    <div class="content">
        <h2>📈 市场概况</h2>
        
        <div class="metric">
            <div class="metric-title">沪深300指数</div>
            <div class="metric-value">{latest['close']:.2f} 
                <span class="{'positive' if price_change >= 0 else 'negative'}">
                    {'+' if price_change >= 0 else ''}{price_change:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                </span>
            </div>
        </div>
        
        {iv_section}
        
        <div class="metric">
            <div class="metric-title">20日历史波动率 (年化)</div>
            <div class="metric-value">{latest['hist_vol']:.2f}% 
                <span class="{'positive' if vol_change >= 0 else 'negative'}">
                    {'+' if vol_change >= 0 else ''}{vol_change:.2f}%
                </span>
            </div>
        </div>
        
        <div class="info-box">
            <strong>💡 数据说明：</strong><br>
            • <strong>隐含波动率(IV)</strong>：从期权价格反推的市场对未来波动的预期，是前瞻性指标<br>
            • <strong>历史波动率</strong>：基于过去20个交易日实际价格波动计算，是回顾性指标<br>
            • IV通常高于历史波动率时，表明市场预期未来波动加大
        </div>
        
        <h2>📊 详细数据</h2>
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
        
        {f"<p>隐含波动率为 {self.iv_data['value']:.2f}%，{'高于' if self.iv_data['value'] > latest['hist_vol'] else '低于'}历史波动率，表明市场预期未来波动{'加大' if self.iv_data['value'] > latest['hist_vol'] else '减小'}。</p>" if self.iv_data else ""}
        
        <p><strong>图表说明：</strong>附件中包含沪深300指数走势及波动率变化图表，请查看附件了解详细趋势。</p>
    </div>
    
    <div class="footer">
        <p>本报告由自动化系统生成 | 数据来源: Tushare, AkShare</p>
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
            server.set_debuglevel(0)
            
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
            return False
        except Exception as e:
            print(f"✗ 邮件发送失败: {e}")
            return False
    
    def run(self, sender_email, sender_password, receiver_email):
        """执行完整流程"""
        print(f"开始生成沪深300波动率简报 - {self.report_date}")
        print("=" * 60)
        
        # 1. 获取指数数据
        print("1. 获取指数数据...")
        df = self.get_index_data(days=60)
        if df is None or df.empty:
            print("✗ 数据获取失败，无法生成报告")
            return False
        print(f"✓ 成功获取 {len(df)} 条数据")
        
        # 2. 获取隐含波动率
        print("2. 获取隐含波动率...")
        iv_value, iv_source = self.get_implied_volatility(df)
        if iv_value:
            print(f"✓ IV: {iv_value:.2f}% (来源: {iv_source})")
        else:
            print("⚠ 未能获取IV数据，报告将只包含历史波动率")
        
        # 3. 生成图表
        print("3. 生成波动率图表...")
        chart_buffer = self.create_volatility_chart(df)
        if chart_buffer:
            print("✓ 图表生成成功")
        else:
            print("⚠ 图表生成失败")
        
        # 4. 生成报告内容
        print("4. 生成报告内容...")
        html_content = self.generate_report_content(df)
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
