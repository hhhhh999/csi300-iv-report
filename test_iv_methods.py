#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多种方法获取沪深300隐含波动率
"""

import sys
from datetime import datetime, timedelta
import numpy as np
from scipy import optimize
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("沪深300隐含波动率获取方法测试")
print("=" * 80)
print()

# ============================================================================
# 方案1: 使用 AkShare 获取期权数据
# ============================================================================
print("【方案1】使用 AkShare 获取沪深300ETF期权数据")
print("-" * 80)

try:
    import akshare as ak
    
    # 获取沪深300ETF期权行情
    print("正在获取沪深300ETF期权行情...")
    
    # 尝试获取510300期权数据
    try:
        df_option = ak.option_sina_sse_list(symbol="510300", exchange="null")
        print(f"✓ 成功获取期权列表，共 {len(df_option)} 条记录")
        print("\n期权列表示例：")
        print(df_option.head())
        
        # 获取具体期权行情
        if not df_option.empty:
            first_code = df_option.iloc[0]['期权代码']
            print(f"\n尝试获取期权 {first_code} 的详细数据...")
            df_detail = ak.option_sina_sse_daily(symbol=first_code)
            print(df_detail.tail())
            
    except Exception as e:
        print(f"✗ AkShare 510300期权数据获取失败: {e}")
        
    # 尝试获取中证指数
    try:
        print("\n尝试获取中证指数数据...")
        df_index = ak.stock_zh_index_daily(symbol="sh000300")
        print(f"✓ 成功获取沪深300指数数据")
        print(df_index.tail())
    except Exception as e:
        print(f"✗ 中证指数数据获取失败: {e}")
        
except ImportError:
    print("✗ AkShare 未安装")
except Exception as e:
    print(f"✗ AkShare 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n")

# ============================================================================
# 方案2: 获取沪深300波动率指数（iVIX）
# ============================================================================
print("【方案2】获取中证沪深300波动率指数（000188.SH）")
print("-" * 80)

try:
    import tushare as ts
    
    # 设置token
    token = "d9e0d91cf2b10940d8d35090ff14bd05feb48f684cea3cd1d67ceac3"
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 获取沪深300波动率指数
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    print(f"正在获取波动率指数数据 (000188.SH)...")
    df_vix = pro.index_daily(
        ts_code='000188.SH',
        start_date=start_date,
        end_date=end_date
    )
    
    if not df_vix.empty:
        df_vix = df_vix.sort_values('trade_date')
        latest = df_vix.iloc[-1]
        print(f"✓ 成功获取沪深300波动率指数")
        print(f"\n最新数据 ({latest['trade_date']}):")
        print(f"  收盘点位: {latest['close']:.2f}")
        print(f"  涨跌幅: {latest['pct_chg']:.2f}%")
        print("\n近期数据：")
        print(df_vix[['trade_date', 'close', 'pct_chg']].tail(10))
    else:
        print("✗ 未获取到波动率指数数据")
        
except Exception as e:
    print(f"✗ 波动率指数获取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n")

# ============================================================================
# 方案3: 通过 Black-Scholes 模型计算隐含波动率
# ============================================================================
print("【方案3】通过期权价格反推隐含波动率（BS模型）")
print("-" * 80)

try:
    import tushare as ts
    
    ts.set_token("d9e0d91cf2b10940d8d35090ff14bd05feb48f684cea3cd1d67ceac3")
    pro = ts.pro_api()
    
    # Black-Scholes 期权定价公式
    def bs_call_price(S, K, T, r, sigma):
        """计算欧式看涨期权价格"""
        if T <= 0:
            return max(S - K, 0)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    def bs_put_price(S, K, T, r, sigma):
        """计算欧式看跌期权价格"""
        if T <= 0:
            return max(K - S, 0)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    def implied_volatility(option_price, S, K, T, r, option_type='call'):
        """反推隐含波动率"""
        if T <= 0:
            return None
            
        def objective(sigma):
            if option_type == 'call':
                return bs_call_price(S, K, T, r, sigma) - option_price
            else:
                return bs_put_price(S, K, T, r, sigma) - option_price
        
        try:
            result = optimize.brentq(objective, 0.001, 5.0)
            return result
        except:
            return None
    
    # 获取沪深300ETF期权数据
    print("正在获取沪深300ETF期权数据...")
    trade_date = datetime.now().strftime('%Y%m%d')
    
    # 获取期权行情
    df_opt = pro.opt_daily(exchange='SSE', trade_date=trade_date)
    
    if df_opt.empty:
        # 尝试前一个交易日
        trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        df_opt = pro.opt_daily(exchange='SSE', trade_date=trade_date)
    
    if not df_opt.empty:
        # 筛选沪深300ETF期权 (510300)
        df_300 = df_opt[df_opt['ts_code'].str.contains('10003')]
        
        if not df_300.empty:
            print(f"✓ 成功获取 {len(df_300)} 条沪深300ETF期权数据")
            
            # 获取标的价格（沪深300ETF）
            df_etf = pro.fund_daily(ts_code='510300.SH', trade_date=trade_date)
            if df_etf.empty:
                trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df_etf = pro.fund_daily(ts_code='510300.SH', trade_date=trade_date)
            
            if not df_etf.empty:
                S = df_etf.iloc[0]['close']
                print(f"  标的价格 (510300.SH): {S:.3f}")
                
                # 获取期权基本信息
                print("\n正在获取期权合约信息...")
                df_basic = pro.opt_basic(exchange='SSE')
                
                # 计算几个期权的隐含波动率
                iv_list = []
                r = 0.02  # 无风险利率假设为2%
                
                print("\n计算隐含波动率示例：")
                print(f"{'期权代码':<20} {'类型':<6} {'行权价':<8} {'期权价格':<10} {'到期天数':<10} {'隐含波动率':<12}")
                print("-" * 80)
                
                for idx, row in df_300.head(10).iterrows():
                    ts_code = row['ts_code']
                    option_price = row['close']
                    
                    # 从基本信息获取行权价和到期日
                    opt_info = df_basic[df_basic['ts_code'] == ts_code]
                    if not opt_info.empty:
                        K = opt_info.iloc[0]['exercise_price']
                        maturity_date = opt_info.iloc[0]['maturity_date']
                        opt_type = 'call' if opt_info.iloc[0]['call_put'] == 'C' else 'put'
                        
                        # 计算到期时间（年）
                        T = (datetime.strptime(maturity_date, '%Y%m%d') - datetime.now()).days / 365.0
                        
                        if T > 0 and option_price > 0:
                            iv = implied_volatility(option_price, S, K, T, r, opt_type)
                            if iv:
                                iv_list.append(iv * 100)  # 转换为百分比
                                print(f"{ts_code:<20} {opt_type:<6} {K:<8.2f} {option_price:<10.4f} {T*365:<10.0f} {iv*100:<12.2f}%")
                
                if iv_list:
                    avg_iv = np.mean(iv_list)
                    print(f"\n✓ 平均隐含波动率: {avg_iv:.2f}%")
                    print(f"  最小值: {min(iv_list):.2f}%")
                    print(f"  最大值: {max(iv_list):.2f}%")
                    print(f"  标准差: {np.std(iv_list):.2f}%")
                else:
                    print("✗ 未能计算出有效的隐含波动率")
            else:
                print("✗ 未获取到标的ETF价格")
        else:
            print("✗ 未找到沪深300ETF期权数据")
    else:
        print("✗ 未获取到期权数据")
        
except Exception as e:
    print(f"✗ BS模型计算失败: {e}")
    import traceback
    traceback.print_exc()

print("\n")
print("=" * 80)
print("测试完成")
print("=" * 80)
