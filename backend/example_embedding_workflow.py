#!/usr/bin/env python3
"""
完整的文档处理工作流示例: 上传 → 加载 → 分块 → 向量化

这个脚本展示了如何使用新的向量嵌入API进行端到端的文档处理。
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000/api"


def upload_document(file_path: str) -> str:
    """步骤1: 上传文档"""
    print("\n=== 步骤1: 上传文档 ===")
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/documents/upload", files=files)
    
    if response.status_code == 200:
        result = response.json()
        document_id = result['data']['id']
        print(f"✅ 文档上传成功")
        print(f"   文档ID: {document_id}")
        print(f"   文件名: {result['data']['filename']}")
        print(f"   大小: {result['data']['size_bytes']} 字节")
        return document_id
    else:
        raise Exception(f"上传失败: {response.text}")


def load_document(document_id: str) -> str:
    """步骤2: 加载文档"""
    print("\n=== 步骤2: 加载文档 ===")
    
    request_data = {
        "document_id": document_id
    }
    
    response = requests.post(f"{BASE_URL}/documents/load", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 文档加载成功")
        print(f"   加载ID: {result['data']['load_id']}")
        print(f"   状态: {result['data']['status']}")
        return result['data']['load_id']
    else:
        raise Exception(f"加载失败: {response.text}")


def chunk_document(document_id: str, strategy: str = "paragraph", chunk_size: int = 500) -> str:
    """步骤3: 分块文档"""
    print("\n=== 步骤3: 分块文档 ===")
    
    request_data = {
        "document_id": document_id,
        "strategy_type": strategy,
        "parameters": {
            "chunk_size": chunk_size,
            "chunk_overlap": 50
        }
    }
    
    response = requests.post(f"{BASE_URL}/chunking/chunk", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 文档分块成功")
        print(f"   结果ID: {result['data']['result_id']}")
        print(f"   分块数量: {result['data']['total_chunks']}")
        print(f"   策略: {result['data']['strategy_type']}")
        return result['data']['result_id']
    else:
        raise Exception(f"分块失败: {response.text}")


def embed_from_chunking_result(result_id: str, model: str = "qwen3-embedding-8b") -> dict:
    """步骤4a: 基于分块结果ID进行向量化"""
    print("\n=== 步骤4a: 向量化(通过分块结果ID) ===")
    
    request_data = {
        "result_id": result_id,
        "model": model,
        "max_retries": 3,
        "timeout": 60
    }
    
    response = requests.post(
        f"{BASE_URL}/embedding/from-chunking-result",
        json=request_data,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 向量化成功")
        print(f"   请求ID: {result['request_id']}")
        print(f"   状态: {result['status']}")
        print(f"   向量数量: {len(result['vectors'])}")
        print(f"   失败数量: {len(result['failures'])}")
        print(f"   处理时间: {result['metadata']['processing_time_ms']:.2f}ms")
        print(f"   吞吐量: {result['metadata']['vectors_per_second']:.2f} vectors/s")
        
        if result['vectors']:
            first_vector = result['vectors'][0]
            print(f"\n   首个向量信息:")
            print(f"     - 维度: {first_vector['dimension']}")
            print(f"     - 文本长度: {first_vector['text_length']}")
            print(f"     - 哈希: {first_vector['text_hash'][:32]}...")
        
        return result
    else:
        raise Exception(f"向量化失败: {response.text}")


def embed_from_document(document_id: str, model: str = "qwen3-embedding-8b", strategy_type: str = None) -> dict:
    """步骤4b: 基于文档ID进行向量化(自动使用最新分块)"""
    print("\n=== 步骤4b: 向量化(通过文档ID) ===")
    
    request_data = {
        "document_id": document_id,
        "model": model,
        "max_retries": 3,
        "timeout": 60
    }
    
    if strategy_type:
        request_data["strategy_type"] = strategy_type
    
    response = requests.post(
        f"{BASE_URL}/embedding/from-document",
        json=request_data,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 向量化成功")
        print(f"   请求ID: {result['request_id']}")
        print(f"   状态: {result['status']}")
        print(f"   向量数量: {len(result['vectors'])}")
        print(f"   处理时间: {result['metadata']['processing_time_ms']:.2f}ms")
        return result
    else:
        raise Exception(f"向量化失败: {response.text}")


def workflow_method_1(file_path: str):
    """
    工作流方法1: 逐步处理,使用分块结果ID
    
    适用场景: 需要精确控制每一步,或需要使用特定的分块结果
    """
    print("\n" + "="*60)
    print("工作流方法1: 逐步处理(使用分块结果ID)")
    print("="*60)
    
    try:
        # 步骤1-3: 上传、加载、分块
        document_id = upload_document(file_path)
        load_id = load_document(document_id)
        
        # 等待加载完成
        print("\n等待加载完成...")
        time.sleep(2)
        
        result_id = chunk_document(document_id, strategy="paragraph", chunk_size=500)
        
        # 步骤4: 向量化
        embedding_result = embed_from_chunking_result(result_id, model="qwen3-embedding-8b")
        
        print("\n" + "="*60)
        print("✅ 工作流完成!")
        print(f"   文档ID: {document_id}")
        print(f"   分块结果ID: {result_id}")
        print(f"   嵌入请求ID: {embedding_result['request_id']}")
        print(f"   向量总数: {len(embedding_result['vectors'])}")
        print("="*60)
        
        return {
            "document_id": document_id,
            "result_id": result_id,
            "embedding_result": embedding_result
        }
    
    except Exception as e:
        print(f"\n❌ 工作流失败: {e}")
        raise


def workflow_method_2(file_path: str):
    """
    工作流方法2: 简化处理,直接使用文档ID
    
    适用场景: 快速处理,自动使用最新的分块结果
    """
    print("\n" + "="*60)
    print("工作流方法2: 简化处理(直接使用文档ID)")
    print("="*60)
    
    try:
        # 步骤1-3: 上传、加载、分块
        document_id = upload_document(file_path)
        load_id = load_document(document_id)
        
        # 等待加载完成
        print("\n等待加载完成...")
        time.sleep(2)
        
        result_id = chunk_document(document_id, strategy="paragraph", chunk_size=500)
        
        # 步骤4: 向量化(直接使用文档ID)
        embedding_result = embed_from_document(
            document_id, 
            model="qwen3-embedding-8b",
            strategy_type="paragraph"
        )
        
        print("\n" + "="*60)
        print("✅ 工作流完成!")
        print(f"   文档ID: {document_id}")
        print(f"   嵌入请求ID: {embedding_result['request_id']}")
        print(f"   向量总数: {len(embedding_result['vectors'])}")
        print("="*60)
        
        return {
            "document_id": document_id,
            "embedding_result": embedding_result
        }
    
    except Exception as e:
        print(f"\n❌ 工作流失败: {e}")
        raise


def main():
    """主函数"""
    import sys
    
    print("="*60)
    print("文档处理完整工作流示例")
    print("="*60)
    
    # 检查后端是否运行
    try:
        response = requests.get(f"{BASE_URL}/embedding/health", timeout=5)
        print(f"✅ 后端服务正常 (状态: {response.json()['status']})")
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("\n请先启动后端服务:")
        print("  cd backend && python -m uvicorn src.main:app --reload")
        sys.exit(1)
    
    # 选择测试文件
    print("\n请提供测试文档路径,或使用示例:")
    file_path = input("文档路径 (按Enter使用示例): ").strip()
    
    if not file_path:
        # 尝试找到示例文件
        example_files = list(Path("../uploads").glob("*.pdf")) if Path("../uploads").exists() else []
        if example_files:
            file_path = str(example_files[0])
            print(f"使用示例文件: {file_path}")
        else:
            print("❌ 未找到示例文件,请提供文档路径")
            sys.exit(1)
    
    # 选择工作流方法
    print("\n选择工作流方法:")
    print("1. 方法1: 逐步处理,使用分块结果ID")
    print("2. 方法2: 简化处理,直接使用文档ID (推荐)")
    print("3. 两种方法都试试")
    
    choice = input("\n输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        workflow_method_1(file_path)
    elif choice == "2":
        workflow_method_2(file_path)
    elif choice == "3":
        print("\n--- 执行方法1 ---")
        result1 = workflow_method_1(file_path)
        
        print("\n\n--- 执行方法2 (使用同一文档) ---")
        result2 = embed_from_document(result1["document_id"])
        
        print("\n" + "="*60)
        print("两种方法对比:")
        print(f"  方法1 向量数: {len(result1['embedding_result']['vectors'])}")
        print(f"  方法2 向量数: {len(result2['vectors'])}")
        print("="*60)
    else:
        print("❌ 无效选择")
        sys.exit(1)


if __name__ == "__main__":
    main()
