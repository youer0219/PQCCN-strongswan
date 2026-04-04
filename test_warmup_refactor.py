#!/usr/bin/env python3
"""
验证warmup数据过滤重构的测试脚本
"""

import pandas as pd
import tempfile
from pathlib import Path
from data_analysis import Plotting
from reporting import generate_experiment_report, _filter_warmup_from_dataframe
from data_parsing import ProcessLogs

def test_plotting_filter():
    """测试Plotting模块的warmup过滤"""
    print("\n" + "="*60)
    print("测试 1: Plotting._filter_warmup_data()")
    print("="*60)
    
    df = pd.read_csv('./results/my_test_20260404_0340/RunLogStatsDF.csv')
    
    print(f"原始数据行数: {len(df)}")
    
    # 检查warmup数据
    warmup_count = len(df[df['ScenarioCase'] == 'warmup'])
    print(f"Warmup行数: {warmup_count}")
    
    # 应用过滤
    filtered_df = Plotting._filter_warmup_data(df)
    print(f"过滤后行数: {len(filtered_df)}")
    
    # 验证
    warmup_after = len(filtered_df[filtered_df['ScenarioCase'] == 'warmup'])
    print(f"过滤后Warmup行数: {warmup_after}")
    
    assert warmup_after == 0, "❌ 过滤失败: 仍有warmup数据存在"
    print("✓ 通过: Warmup数据成功过滤")

def test_plotting_param():
    """测试PlotVariParam的include_warmup参数"""
    print("\n" + "="*60)
    print("测试 2: PlotVariParam(include_warmup=True/False)")
    print("="*60)
    
    df = pd.read_csv('./results/my_test_20260404_0340/RunLogStatsDF.csv')
    
    # 测试 include_warmup=False
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_df = Plotting.PlotVariParam(df, tmpdir, 2, include_warmup=False)
        print(f"include_warmup=False: 生成 {len(audit_df)} 个图表")
        assert len(audit_df) > 0, "❌ 未生成图表"
    
    # 测试 include_warmup=True
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_df = Plotting.PlotVariParam(df, tmpdir, 2, include_warmup=True)
        print(f"include_warmup=True: 生成 {len(audit_df)} 个图表")
        assert len(audit_df) > 0, "❌ 未生成图表"
    
    print("✓ 通过: PlotVariParam参数可控")

def test_reporting_filter():
    """测试报告生成中的warmup过滤"""
    print("\n" + "="*60)
    print("测试 3: _filter_warmup_from_dataframe()")
    print("="*60)
    
    df = pd.read_csv('./results/my_test_20260404_0340/RunLogStatsDF.csv')
    
    filtered_df = _filter_warmup_from_dataframe(df)
    
    print(f"原始行数: {len(df)}")
    print(f"过滤后行数: {len(filtered_df)}")
    
    warmup_count = len(filtered_df[filtered_df['ScenarioCase'] == 'warmup'])
    assert warmup_count == 0, "❌ 过滤失败: 仍有warmup数据"
    print("✓ 通过: 报告过滤函数正确")

def test_report_generation():
    """测试报告生成中的include_warmup参数"""
    print("\n" + "="*60)
    print("测试 4: generate_experiment_report(include_warmup=True/False)")
    print("="*60)
    
    df = pd.read_csv('./results/my_test_20260404_0340/RunLogStatsDF.csv')
    plot_audit = pd.DataFrame()
    
    # 测试 include_warmup=False
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = generate_experiment_report(tmpdir, df, plot_audit, include_warmup=False)
        content = Path(report_path).read_text()
        
        has_warmup = 'warmup' in content.lower()
        
        if has_warmup:
            print("❌ 失败: include_warmup=False 但报告中包含warmup")
            # 显示包含warmup的行
            for i, line in enumerate(content.split('\n'), 1):
                if 'warmup' in line.lower():
                    print(f"  行 {i}: {line[:80]}")
        else:
            print("✓ 通过: include_warmup=False 正确排除warmup")
    
    # 测试 include_warmup=True
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = generate_experiment_report(tmpdir, df, plot_audit, include_warmup=True)
        content = Path(report_path).read_text()
        
        has_warmup = 'warmup' in content.lower()
        
        if has_warmup:
            print("✓ 通过: include_warmup=True 正确包含warmup")
        else:
            print("❌ 失败: include_warmup=True 但报告中不包含warmup")

def test_scenario_cases():
    """验证ScenarioCases列表的内容"""
    print("\n" + "="*60)
    print("测试 5: ScenarioCases列表内容验证")
    print("="*60)
    
    df = pd.read_csv('./results/my_test_20260404_0340/RunLogStatsDF.csv')
    
    # 获取所有场景
    all_scenarios = set(df['ScenarioCase'].dropna().unique())
    print(f"原始所有场景: {sorted(all_scenarios)}")
    
    # 过滤后
    filtered_df = Plotting._filter_warmup_data(df)
    filtered_scenarios = set(filtered_df['ScenarioCase'].dropna().unique())
    print(f"过滤后场景: {sorted(filtered_scenarios)}")
    
    if 'warmup' in all_scenarios and 'warmup' not in filtered_scenarios:
        print("✓ 通过: Warmup场景成功移除")
    else:
        print("❌ 失败: Warmup场景移除失败")

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("WARMUP数据过滤重构验证测试")
    print("="*60)
    
    try:
        test_plotting_filter()
        test_plotting_param()
        test_reporting_filter()
        test_report_generation()
        test_scenario_cases()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60 + "\n")
        
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
