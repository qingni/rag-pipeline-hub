"""BM25 Sparse Generator 快速验证测试"""
import sys
import os
import tempfile
import logging
import types

# 在导入 bm25_service 之前，先 mock 掉它的相对导入依赖
# 创建 mock 的 utils.logger 模块
def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
        logger.addHandler(handler)
    return logger

# 设置项目路径
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'src'))

# 创建包结构的 mock
# 需要 mock src.utils.logger
mock_utils_logger = types.ModuleType("src.utils.logger")
mock_utils_logger.get_logger = get_logger
sys.modules["src.utils.logger"] = mock_utils_logger

# 直接导入 bm25_service 中的核心类（绕过相对导入）
import importlib.util
bm25_path = os.path.join(backend_dir, 'src', 'services', 'bm25_service.py')

# 读取源码，替换相对导入为绝对导入
source = open(bm25_path).read()
source = source.replace("from ..utils.logger import get_logger", "from src.utils.logger import get_logger")

# 编译并执行
code = compile(source, bm25_path, 'exec')
module_globals = {"__name__": "bm25_service", "__file__": bm25_path}
exec(code, module_globals)

# 从执行结果中提取类
BM25SparseGenerator = module_globals["BM25SparseGenerator"]
BM25SparseService = module_globals["BM25SparseService"]
JIEBA_AVAILABLE = module_globals["JIEBA_AVAILABLE"]

print("=== BM25 Sparse Generator Test ===")
print(f"jieba available: {JIEBA_AVAILABLE}")

# 测试中文语料
corpus = [
    '向量索引是RAG系统中用于快速检索文档片段的核心组件',
    '混合检索结合了稠密向量和稀疏向量的优势',
    'BM25是一种经典的基于统计的稀疏检索方法',
    '深度学习模型可以生成高质量的文本向量表示',
    'Milvus是一个开源的向量数据库支持多种索引算法',
]

# 1. 测试 fit
gen = BM25SparseGenerator()
gen.fit(corpus)
print(f"\n[1] Fit: vocab={len(gen.vocab)}, avgdl={gen.avgdl:.1f}, docs={gen.doc_count}")
assert gen.is_fitted
assert len(gen.vocab) > 0
assert gen.doc_count == 5

# 2. 测试文档编码
doc_sparse = gen.encode_document(corpus[0])
print(f"[2] Doc encode: {len(doc_sparse)} non-zero dims")
assert len(doc_sparse) > 0
for k, v in doc_sparse.items():
    assert isinstance(k, int), f"Key should be int, got {type(k)}"
    assert isinstance(v, float), f"Value should be float, got {type(v)}"
    assert v > 0, f"Weight should be positive, got {v}"

# 3. 测试查询编码
query_sparse = gen.encode_query('向量检索')
print(f"[3] Query encode: {len(query_sparse)} non-zero dims")
assert len(query_sparse) > 0

# 4. 测试批量编码
batch_sparse = gen.encode_documents(corpus)
print(f"[4] Batch encode: {len(batch_sparse)} vectors, {sum(1 for sv in batch_sparse if sv)} non-empty")
assert len(batch_sparse) == len(corpus)

# 5. 测试持久化
tmpdir = tempfile.mkdtemp()
stats_path = os.path.join(tmpdir, 'test_bm25_stats.json')
gen.save_stats(stats_path)
assert os.path.exists(stats_path)
print(f"[5] Stats saved OK")

# 6. 测试加载
gen2 = BM25SparseGenerator.load_stats(stats_path)
query_sparse2 = gen2.encode_query('向量检索')
assert query_sparse2 == query_sparse, "Loaded generator should produce same results"
print(f"[6] Stats loaded, results match: True")

# 7. 测试 BM25SparseService
service = BM25SparseService(stats_dir=tmpdir)
sparse_vecs = service.build_and_encode('test-index-001', corpus)
print(f"[7] Service build_and_encode: {len(sparse_vecs)} vectors")
assert len(sparse_vecs) == len(corpus)

query_sv = service.encode_query('test-index-001', '向量检索')
print(f"[8] Service encode_query: {len(query_sv) if query_sv else 0} non-zero dims")
assert query_sv is not None and len(query_sv) > 0

# 8. 测试 has_stats
assert service.has_stats('test-index-001')
assert not service.has_stats('non-existent-index')
print(f"[9] has_stats check: OK")

# 9. 测试空语料
gen_empty = BM25SparseGenerator()
gen_empty.fit([])
assert not gen_empty.is_fitted
empty_sparse = gen_empty.encode_document("test")
assert empty_sparse == {}
print(f"[10] Empty corpus: OK")

# 10. 测试 Milvus 兼容格式（key 是 int）
for sv in sparse_vecs:
    if sv:
        for k in sv.keys():
            assert isinstance(k, int), f"Milvus requires int keys, got {type(k)}: {k}"
print(f"[11] Milvus format compat: OK")

# 清理
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

print("\n=== All 11 tests passed! ===")
