#!/usr/bin/env python3
"""测试 HybridChunker 标题信息注入功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.providers.chunkers.hybrid_chunker import HybridChunker

test_text = """# 股票 APP 交易功能页面

## 一、页面顶部区域

### 1. 搜索栏
提供股票代码和名称的搜索功能，支持模糊搜索。

### 2. 账户信息
显示当前账户的总资产、可用余额等关键数据。

## 二、交易内容展示区

### 1. 买入功能
用户可以输入股票代码、买入价格和买入数量进行委托下单。

### 2. 卖出功能
用户可以选择持仓股票，输入卖出价格和数量进行委托卖出。

## 三、底部导航栏

### 1. 新闻
点击切换至新闻资讯页面，获取最新市场动态。

### 2. 行情
点击切换至行情页面，查看实时股票行情数据。
"""

def test_strategy(name, **params):
    print(f"\n{'='*60}")
    print(f"策略: {name}")
    print(f"{'='*60}")
    chunker = HybridChunker(
        include_tables=False,
        include_code=False,
        include_images=False,
        **params
    )
    chunks = chunker.chunk(test_text)
    print(f"共产出 {len(chunks)} 个 chunk\n")
    
    for i, c in enumerate(chunks):
        m = c['metadata']
        hp = m.get('heading_path', '无')
        st = m.get('section_title', '无')
        ph = m.get('parent_heading', '无')
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  Chunk {i}:")
        print(f"    heading_path:   {hp}")
        print(f"    section_title:  {st}")
        print(f"    parent_heading: {ph}")
        print(f"    内容: {content_preview}...")
        print()

# 测试 1: character 策略
test_strategy("character", text_strategy='character', text_chunk_size=150, text_overlap=20)

# 测试 2: paragraph 策略
test_strategy("paragraph", text_strategy='paragraph', text_chunk_size=500, text_overlap=50)

# 测试 3: heading 策略（应保持原有行为）
test_strategy("heading", text_strategy='heading', min_heading_level=1, max_heading_level=3)

print("\n全部测试完成!")
