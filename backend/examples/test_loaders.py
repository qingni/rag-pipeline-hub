#!/usr/bin/env python3
"""
测试不同文档格式的加载器

这个脚本演示如何使用新的文档加载器加载不同格式的文档。
注意: 需要安装相应的依赖包才能运行完整测试。
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_result(result, loader_name):
    """打印加载结果"""
    print(f"\n{'='*60}")
    print(f"Loader: {loader_name}")
    print(f"{'='*60}")
    
    if result.get("success"):
        print(f"✓ 加载成功")
        print(f"  - 总页数: {result.get('total_pages', 0)}")
        print(f"  - 总字符数: {result.get('total_chars', 0)}")
        
        # 打印元数据
        metadata = result.get("metadata", {})
        if metadata:
            print(f"\n元数据:")
            for key, value in metadata.items():
                if value:
                    print(f"  - {key}: {value}")
        
        # 打印文本预览
        full_text = result.get("full_text", "")
        if full_text:
            preview = full_text[:200].replace("\n", " ")
            print(f"\n文本预览:")
            print(f"  {preview}...")
    else:
        print(f"✗ 加载失败")
        print(f"  错误: {result.get('error', 'Unknown error')}")


def test_text_loader():
    """测试文本加载器"""
    print("\n" + "="*60)
    print("测试文本加载器")
    print("="*60)
    
    try:
        from src.providers.loaders.text_loader import text_loader
        
        # 创建测试文本文件
        test_file = "/tmp/test_document.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文档。\n")
            f.write("用于测试文本加载器的功能。\n")
            f.write("支持多行文本。\n")
        
        result = text_loader.extract_text(test_file)
        print_result(result, "Text Loader")
        
        # 清理
        os.remove(test_file)
    except Exception as e:
        print(f"✗ 测试失败: {e}")


def test_markdown_loader():
    """测试 Markdown 加载器"""
    print("\n" + "="*60)
    print("测试 Markdown 加载器")
    print("="*60)
    
    try:
        from src.providers.loaders.text_loader import text_loader
        
        # 创建测试 Markdown 文件
        test_file = "/tmp/test_document.md"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("# 测试标题\n\n")
            f.write("## 第一节\n\n")
            f.write("这是测试内容。\n\n")
            f.write("- 列表项 1\n")
            f.write("- 列表项 2\n")
        
        result = text_loader.extract_text(test_file)
        print_result(result, "Markdown Loader (Text)")
        
        # 清理
        os.remove(test_file)
    except Exception as e:
        print(f"✗ 测试失败: {e}")


def test_docx_loader():
    """测试 DOCX 加载器"""
    print("\n" + "="*60)
    print("测试 DOCX 加载器")
    print("="*60)
    
    # 检查是否安装了 python-docx
    try:
        import docx
        print("✓ python-docx 已安装")
    except ImportError:
        print("✗ python-docx 未安装")
        print("  安装命令: pip install python-docx")
        return
    
    print("\n提示: 请提供一个 .docx 文件路径进行测试")
    print("示例: /path/to/your/document.docx")


def test_doc_loader():
    """测试 DOC 加载器"""
    print("\n" + "="*60)
    print("测试 DOC 加载器")
    print("="*60)
    
    # 检查可用的提取工具
    import subprocess
    
    # 检查 antiword
    try:
        subprocess.run(['antiword', '-v'], capture_output=True, timeout=2)
        print("✓ antiword 已安装")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("✗ antiword 未安装")
        print("  Linux: sudo apt-get install antiword")
        print("  macOS: brew install antiword")
    
    # 检查 textract
    try:
        import textract
        print("✓ textract 已安装")
    except ImportError:
        print("✗ textract 未安装")
        print("  安装命令: pip install textract")
    
    print("\n提示: 请提供一个 .doc 文件路径进行测试")
    print("示例: /path/to/your/document.doc")


def test_loading_service():
    """测试加载服务"""
    print("\n" + "="*60)
    print("测试加载服务")
    print("="*60)
    
    try:
        from src.services.loading_service import loading_service
        
        print("\n可用的加载器:")
        for loader in loading_service.get_available_loaders():
            print(f"  - {loader}")
        
        print("\n支持的文件格式:")
        for fmt in loading_service.get_supported_formats():
            loader = loading_service.get_loader_for_format(fmt)
            print(f"  - .{fmt} -> {loader}")
        
        print("\n格式到加载器的映射:")
        for fmt, loader in loading_service.format_loader_map.items():
            print(f"  - {fmt}: {loader}")
    except Exception as e:
        print(f"✗ 测试失败: {e}")


def main():
    """主函数"""
    print("="*60)
    print("文档加载器测试工具")
    print("="*60)
    
    # 测试加载服务
    test_loading_service()
    
    # 测试文本加载器
    test_text_loader()
    
    # 测试 Markdown 加载器
    test_markdown_loader()
    
    # 测试 DOCX 加载器
    test_docx_loader()
    
    # 测试 DOC 加载器
    test_doc_loader()
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()
