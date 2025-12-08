"""
Test script for Document Selector API optimization
测试文档选择器 API 优化功能
"""
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/chunking"


def print_result(title: str, data: Dict[Any, Any]):
    """打印测试结果"""
    print("\n" + "="*60)
    print(f"📊 {title}")
    print("="*60)
    if 'success' in data and data['success']:
        print("✅ 请求成功")
        if 'data' in data:
            result_data = data['data']
            if 'total' in result_data:
                print(f"📁 总文档数: {result_data['total']}")
            if 'items' in result_data:
                print(f"📄 当前页文档数: {len(result_data['items'])}")
                print(f"📑 页码: {result_data.get('page', 'N/A')}")
                print(f"📏 每页大小: {result_data.get('page_size', 'N/A')}")
                
                # 显示前3个文档
                if result_data['items']:
                    print("\n前3个文档:")
                    for i, doc in enumerate(result_data['items'][:3], 1):
                        print(f"  {i}. {doc.get('filename', 'N/A')} "
                              f"({doc.get('format', 'N/A')}, "
                              f"{doc.get('size_bytes', 0)/1024:.1f}KB)")
    else:
        print("❌ 请求失败")
        print(f"错误信息: {data.get('message', 'Unknown error')}")


def test_basic_pagination():
    """测试1: 基本分页功能"""
    print("\n🧪 测试1: 基本分页功能")
    
    # 第1页
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 10
    })
    print_result("第1页 (10条/页)", response.json())
    
    # 第2页
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 2,
        "page_size": 10
    })
    print_result("第2页 (10条/页)", response.json())


def test_search_filter():
    """测试2: 搜索过滤功能"""
    print("\n🧪 测试2: 搜索过滤功能")
    
    # 搜索文件名
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 20,
        "search": "test"
    })
    print_result("搜索 'test'", response.json())
    
    # 搜索另一个关键词
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 20,
        "search": "document"
    })
    print_result("搜索 'document'", response.json())


def test_format_filter():
    """测试3: 文件类型过滤"""
    print("\n🧪 测试3: 文件类型过滤")
    
    for format_type in ['pdf', 'txt', 'docx', 'md']:
        response = requests.get(f"{BASE_URL}/documents/parsed", params={
            "page": 1,
            "page_size": 20,
            "format": format_type
        })
        print_result(f"过滤 {format_type.upper()} 文件", response.json())


def test_sorting():
    """测试4: 排序功能"""
    print("\n🧪 测试4: 排序功能")
    
    # 按文件名升序
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 5,
        "sort_by": "filename",
        "sort_order": "asc"
    })
    print_result("按文件名升序", response.json())
    
    # 按上传时间降序
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 5,
        "sort_by": "upload_time",
        "sort_order": "desc"
    })
    print_result("按上传时间降序", response.json())
    
    # 按文件大小降序
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 5,
        "sort_by": "size_bytes",
        "sort_order": "desc"
    })
    print_result("按文件大小降序", response.json())


def test_combined_filters():
    """测试5: 组合过滤"""
    print("\n🧪 测试5: 组合过滤")
    
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 20,
        "search": "test",
        "format": "pdf",
        "sort_by": "upload_time",
        "sort_order": "desc"
    })
    print_result("组合: 搜索'test' + PDF + 按时间降序", response.json())


def test_performance():
    """测试6: 性能测试"""
    print("\n🧪 测试6: 性能测试")
    
    # 测试不同页面大小的响应时间
    page_sizes = [10, 20, 50, 100]
    
    for page_size in page_sizes:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/documents/parsed", params={
            "page": 1,
            "page_size": page_size
        })
        elapsed_time = time.time() - start_time
        
        data = response.json()
        if data.get('success'):
            items_count = len(data['data'].get('items', []))
            print(f"✅ 页面大小 {page_size}: {elapsed_time*1000:.2f}ms (返回 {items_count} 条)")
        else:
            print(f"❌ 页面大小 {page_size}: 请求失败")


def test_edge_cases():
    """测试7: 边界情况"""
    print("\n🧪 测试7: 边界情况")
    
    # 空搜索结果
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 20,
        "search": "nonexistent_file_xyz123"
    })
    print_result("搜索不存在的文件", response.json())
    
    # 超大页码
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 9999,
        "page_size": 20
    })
    print_result("超大页码 (9999)", response.json())
    
    # 最小页面大小
    response = requests.get(f"{BASE_URL}/documents/parsed", params={
        "page": 1,
        "page_size": 1
    })
    print_result("最小页面大小 (1)", response.json())


def main():
    """运行所有测试"""
    print("\n" + "🚀 "*20)
    print("文档选择器 API 优化测试")
    print("🚀 "*20)
    
    try:
        # 检查服务是否运行
        response = requests.get(f"{BASE_URL}/strategies")
        if not response.ok:
            print("❌ 后端服务未运行或无法访问")
            print(f"请确保后端服务运行在 {BASE_URL}")
            return
        
        print("✅ 后端服务正常运行\n")
        
        # 运行测试
        test_basic_pagination()
        test_search_filter()
        test_format_filter()
        test_sorting()
        test_combined_filters()
        test_performance()
        test_edge_cases()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到后端服务: {BASE_URL}")
        print("请确保后端服务正在运行")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
