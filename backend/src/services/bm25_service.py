"""
BM25 稀疏向量生成服务

基于 BM25 算法生成稀疏向量，用于混合检索中的稀疏向量路。
采用 jieba 分词 + 自建词表方案，轻量级，无需 GPU 或大模型。

主要功能：
- 从文档分块语料库自动构建 IDF 统计信息
- 为文档和查询生成 BM25 稀疏向量
- IDF 统计信息的持久化和加载
- 输出格式与 Milvus SPARSE_FLOAT_VECTOR 完全兼容
"""
import json
import math
import os
import time
from collections import Counter
from typing import Dict, List, Optional, Any

from ..utils.logger import get_logger

logger = get_logger("bm25_service")

# 尝试导入 jieba，不可用时使用简单分词回退
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，将使用简单字符级分词。建议安装 jieba: pip install jieba")


def _simple_tokenize(text: str) -> List[str]:
    """
    简单分词回退方案（当 jieba 不可用时）
    
    对中文按字符切分，对英文按空格切分。
    精度不如 jieba，但可以保证基本功能可用。
    """
    import re
    # 提取中文字符和英文单词
    tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', text.lower())
    return tokens


def tokenize(text: str) -> List[str]:
    """
    对文本进行分词
    
    优先使用 jieba 精确模式分词，不可用时回退到简单分词。
    自动过滤停用词和单字符词。
    """
    if JIEBA_AVAILABLE:
        # jieba 精确模式分词
        tokens = list(jieba.cut(text, cut_all=False))
    else:
        tokens = _simple_tokenize(text)
    
    # 过滤：去除空白、标点符号和过短的 token
    filtered = []
    for token in tokens:
        token = token.strip()
        if len(token) == 0:
            continue
        # 过滤纯标点和空白
        if all(c in '，。！？、；：""''（）【】《》—…·\n\r\t ,.!?;:\'"()[]{}/-_=+' for c in token):
            continue
        filtered.append(token)
    
    return filtered


# 中文停用词表（常见高频无意义词）
CHINESE_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么", "这个", "那个",
    "但", "而", "或", "如果", "因为", "所以", "虽然", "但是", "可以", "能", "被",
    "把", "从", "对", "与", "以", "及", "等", "为", "于", "中", "之", "其",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "or", "but", "if", "while", "of", "at", "by", "for", "with",
    "about", "between", "through", "during", "before", "after", "above",
    "below", "to", "from", "in", "out", "on", "off", "over", "under",
    "this", "that", "these", "those", "it", "its", "not", "no", "nor",
}


class BM25SparseGenerator:
    """
    基于 BM25 的稀疏向量生成器
    
    使用 BM25 算法为文档和查询生成稀疏向量，
    输出格式为 {token_id: bm25_weight}，与 Milvus SPARSE_FLOAT_VECTOR 兼容。
    
    工作流程：
    1. fit(): 从语料库构建词表和 IDF 统计
    2. encode_document(): 为单个文档生成 BM25 稀疏向量
    3. encode_documents(): 批量为文档生成稀疏向量
    4. encode_query(): 为查询生成稀疏向量
    5. save_stats() / load_stats(): 持久化/加载 IDF 统计
    
    BM25 参数说明：
    - k1: 词频饱和参数，控制词频对分数的影响程度。k1 越大，高词频文档得分越高。
           典型范围 [1.2, 2.0]，默认 1.5
    - b:  文档长度归一化参数。b=0 不做归一化，b=1 完全归一化。
           典型值 0.75
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        min_df: int = 1,
        max_df_ratio: float = 0.95,
        enable_stopwords: bool = True
    ):
        """
        初始化 BM25 稀疏向量生成器
        
        Args:
            k1: BM25 词频饱和参数，默认 1.5
            b: BM25 文档长度归一化参数，默认 0.75
            min_df: 最小文档频率，低于此值的词将被忽略（过滤极稀有词）
            max_df_ratio: 最大文档频率比例，高于此比例的词将被忽略（过滤停用词级高频词）
            enable_stopwords: 是否启用停用词过滤
        """
        self.k1 = k1
        self.b = b
        self.min_df = min_df
        self.max_df_ratio = max_df_ratio
        self.enable_stopwords = enable_stopwords
        
        # 内部状态（fit 后填充）
        self.vocab: Dict[str, int] = {}       # token → token_id 映射
        self.idf: Dict[str, float] = {}       # token → IDF 值
        self.avgdl: float = 0.0               # 平均文档长度
        self.doc_count: int = 0               # 语料库文档总数
        self.df: Dict[str, int] = {}          # token → 文档频率
        self._fitted: bool = False
    
    def fit(self, corpus: List[str]) -> "BM25SparseGenerator":
        """
        从语料库构建 BM25 统计信息
        
        遍历所有文档，计算：
        1. 词表（vocab）：所有出现过的词 → 整数 ID 映射
        2. 文档频率（df）：每个词出现在多少个文档中
        3. 逆文档频率（IDF）：每个词的区分度
        4. 平均文档长度（avgdl）：用于文档长度归一化
        
        Args:
            corpus: 文档文本列表（通常是分块后的 chunks）
            
        Returns:
            self（支持链式调用）
        """
        start_time = time.time()
        
        if not corpus:
            logger.warning("语料库为空，无法构建 BM25 统计信息")
            return self
        
        self.doc_count = len(corpus)
        doc_lengths = []
        token_df: Counter = Counter()  # 记录每个 token 出现在多少个文档中
        all_tokens_set: set = set()
        
        # 第一遍遍历：计算文档频率和平均文档长度
        for doc_text in corpus:
            tokens = self._tokenize_and_filter(doc_text)
            doc_lengths.append(len(tokens))
            
            # 每个文档中出现的唯一 token（计算 df）
            unique_tokens = set(tokens)
            for token in unique_tokens:
                token_df[token] += 1
            all_tokens_set.update(unique_tokens)
        
        self.avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0
        
        # 构建词表：过滤极低频和极高频词
        max_df = int(self.doc_count * self.max_df_ratio)
        vocab_id = 0
        
        for token in sorted(all_tokens_set):  # 排序确保可重复性
            df = token_df[token]
            if df < self.min_df:
                continue  # 过滤极稀有词
            if df > max_df:
                continue  # 过滤极高频词（类停用词）
            self.vocab[token] = vocab_id
            vocab_id += 1
        
        # 保存文档频率
        self.df = {token: token_df[token] for token in self.vocab}
        
        # 计算 IDF（使用 BM25 标准 IDF 公式）
        self.idf = {}
        for token, df in self.df.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            # 加 1 是为了避免负值（当 df > N/2 时原始公式可能为负）
            self.idf[token] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
        
        self._fitted = True
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"BM25 fit 完成: {self.doc_count} 个文档, "
            f"词表大小 {len(self.vocab)}, "
            f"平均文档长度 {self.avgdl:.1f} 个 token, "
            f"耗时 {elapsed_ms:.1f}ms"
        )
        
        return self
    
    def encode_document(self, text: str) -> Dict[int, float]:
        """
        为单个文档生成 BM25 稀疏向量
        
        BM25 公式：
        BM25(t, d) = IDF(t) × [tf(t,d) × (k1 + 1)] / [tf(t,d) + k1 × (1 - b + b × |d|/avgdl)]
        
        Args:
            text: 文档文本
            
        Returns:
            稀疏向量 {token_id: bm25_weight}，只包含非零维度
        """
        if not self._fitted:
            logger.warning("BM25 尚未 fit，返回空稀疏向量")
            return {}
        
        tokens = self._tokenize_and_filter(text)
        if not tokens:
            return {}
        
        doc_len = len(tokens)
        tf_counter = Counter(tokens)
        sparse_vector: Dict[int, float] = {}
        
        for token, tf in tf_counter.items():
            if token not in self.vocab:
                continue
            
            token_id = self.vocab[token]
            idf = self.idf.get(token, 0.0)
            
            # BM25 TF 饱和公式
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            
            weight = idf * (numerator / denominator)
            
            if weight > 0:
                sparse_vector[token_id] = round(weight, 6)
        
        return sparse_vector
    
    def encode_documents(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        批量为文档生成 BM25 稀疏向量
        
        Args:
            texts: 文档文本列表
            
        Returns:
            稀疏向量列表
        """
        start_time = time.time()
        results = [self.encode_document(text) for text in texts]
        elapsed_ms = (time.time() - start_time) * 1000
        
        non_empty = sum(1 for r in results if r)
        logger.info(
            f"BM25 批量编码完成: {len(texts)} 个文档, "
            f"{non_empty} 个非空稀疏向量, "
            f"耗时 {elapsed_ms:.1f}ms"
        )
        
        return results
    
    def encode_query(self, query_text: str) -> Dict[int, float]:
        """
        为查询文本生成 BM25 稀疏向量
        
        查询侧的 BM25 权重采用简化公式：
        query_weight(t) = IDF(t) × tf(t, q)
        
        这是标准 BM25 检索中查询侧的标准处理方式。
        查询通常很短，TF 饱和函数的简化影响极小。
        
        Args:
            query_text: 查询文本
            
        Returns:
            稀疏向量 {token_id: idf_weight}
        """
        if not self._fitted:
            logger.warning("BM25 尚未 fit，返回空稀疏向量")
            return {}
        
        tokens = self._tokenize_and_filter(query_text)
        if not tokens:
            return {}
        
        tf_counter = Counter(tokens)
        sparse_vector: Dict[int, float] = {}
        
        for token, tf in tf_counter.items():
            if token not in self.vocab:
                continue
            
            token_id = self.vocab[token]
            idf = self.idf.get(token, 0.0)
            
            # 查询侧权重 = IDF × 查询中的词频
            weight = idf * tf
            
            if weight > 0:
                sparse_vector[token_id] = round(weight, 6)
        
        return sparse_vector
    
    def save_stats(self, filepath: str) -> None:
        """
        将 BM25 统计信息持久化到 JSON 文件
        
        持久化内容包括：vocab、idf、df、avgdl、doc_count 和 BM25 参数。
        用于后续查询时加载相同的统计信息，确保索引时和查询时的一致性。
        
        Args:
            filepath: JSON 文件保存路径
        """
        if not self._fitted:
            logger.warning("BM25 尚未 fit，无法保存统计信息")
            return
        
        data = {
            "version": "1.0",
            "params": {
                "k1": self.k1,
                "b": self.b,
                "min_df": self.min_df,
                "max_df_ratio": self.max_df_ratio,
                "enable_stopwords": self.enable_stopwords,
            },
            "stats": {
                "doc_count": self.doc_count,
                "avgdl": self.avgdl,
                "vocab_size": len(self.vocab),
            },
            "vocab": self.vocab,
            "idf": self.idf,
            "df": {k: v for k, v in self.df.items()},
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"BM25 统计信息已保存到 {filepath}")
    
    @classmethod
    def load_stats(cls, filepath: str) -> "BM25SparseGenerator":
        """
        从 JSON 文件加载 BM25 统计信息
        
        Args:
            filepath: JSON 文件路径
            
        Returns:
            已加载统计信息的 BM25SparseGenerator 实例
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"BM25 统计文件不存在: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        params = data.get("params", {})
        generator = cls(
            k1=params.get("k1", 1.5),
            b=params.get("b", 0.75),
            min_df=params.get("min_df", 1),
            max_df_ratio=params.get("max_df_ratio", 0.95),
            enable_stopwords=params.get("enable_stopwords", True),
        )
        
        stats = data.get("stats", {})
        generator.doc_count = stats.get("doc_count", 0)
        generator.avgdl = stats.get("avgdl", 0.0)
        generator.vocab = data.get("vocab", {})
        generator.idf = data.get("idf", {})
        generator.df = data.get("df", {})
        generator._fitted = True
        
        logger.info(
            f"BM25 统计信息已从 {filepath} 加载: "
            f"{generator.doc_count} 个文档, 词表大小 {len(generator.vocab)}"
        )
        
        return generator
    
    def _tokenize_and_filter(self, text: str) -> List[str]:
        """
        对文本进行分词并过滤停用词
        
        Args:
            text: 输入文本
            
        Returns:
            过滤后的 token 列表
        """
        tokens = tokenize(text)
        
        if self.enable_stopwords:
            tokens = [t for t in tokens if t.lower() not in CHINESE_STOPWORDS]
        
        return tokens
    
    @property
    def is_fitted(self) -> bool:
        """是否已完成 fit"""
        return self._fitted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 BM25 统计摘要信息"""
        return {
            "fitted": self._fitted,
            "doc_count": self.doc_count,
            "vocab_size": len(self.vocab),
            "avgdl": round(self.avgdl, 2),
            "k1": self.k1,
            "b": self.b,
            "jieba_available": JIEBA_AVAILABLE,
        }


class BM25SparseService:
    """
    BM25 稀疏向量服务（面向索引构建和查询的高层接口）
    
    封装 BM25SparseGenerator，提供：
    - 从文档分块构建 BM25 统计并生成 sparse 向量
    - 按索引 ID 管理 BM25 统计信息（持久化到磁盘）
    - 查询时自动加载对应索引的 BM25 统计来生成 query sparse 向量
    """
    
    def __init__(self, stats_dir: str = "results/bm25_stats"):
        """
        初始化 BM25 稀疏向量服务
        
        Args:
            stats_dir: BM25 统计信息的持久化目录
        """
        self.stats_dir = stats_dir
        os.makedirs(stats_dir, exist_ok=True)
        
        # 缓存已加载的 BM25 生成器（按索引 ID）
        self._generators: Dict[str, BM25SparseGenerator] = {}
    
    def build_and_encode(
        self,
        index_id: str,
        texts: List[str]
    ) -> List[Dict[int, float]]:
        """
        从文本列表构建 BM25 统计信息并生成稀疏向量
        
        这是索引构建时的核心方法：
        1. 用所有文本作为语料库 fit BM25
        2. 为每个文本生成 sparse 向量
        3. 持久化 BM25 统计信息（用于后续查询）
        
        Args:
            index_id: 索引 ID（用于关联 BM25 统计）
            texts: 文档文本列表
            
        Returns:
            稀疏向量列表，每个元素为 {token_id: weight}
        """
        if not texts:
            logger.warning(f"索引 {index_id} 的文本列表为空，跳过 BM25")
            return []
        
        start_time = time.time()
        
        # 1. 构建 BM25 统计
        generator = BM25SparseGenerator()
        generator.fit(texts)
        
        # 2. 为每个文档生成稀疏向量
        sparse_vectors = generator.encode_documents(texts)
        
        # 3. 持久化 BM25 统计
        stats_path = self._get_stats_path(index_id)
        generator.save_stats(stats_path)
        
        # 4. 缓存
        self._generators[index_id] = generator
        
        elapsed_ms = (time.time() - start_time) * 1000
        non_empty = sum(1 for sv in sparse_vectors if sv)
        logger.info(
            f"BM25 build_and_encode 完成: 索引={index_id}, "
            f"{len(texts)} 个文档, {non_empty} 个非空稀疏向量, "
            f"耗时 {elapsed_ms:.1f}ms"
        )
        
        return sparse_vectors
    
    def encode_query(self, index_id: str, query_text: str) -> Optional[Dict[int, float]]:
        """
        为查询文本生成 BM25 稀疏向量
        
        自动加载对应索引的 BM25 统计信息（从缓存或磁盘）。
        
        Args:
            index_id: 索引 ID
            query_text: 查询文本
            
        Returns:
            稀疏向量 {token_id: weight}，如果加载失败返回 None
        """
        generator = self._get_generator(index_id)
        if generator is None:
            logger.warning(f"无法加载索引 {index_id} 的 BM25 统计信息，返回空稀疏向量")
            return None
        
        sparse_vector = generator.encode_query(query_text)
        
        if sparse_vector:
            logger.debug(
                f"BM25 query 编码: 索引={index_id}, "
                f"非零维度={len(sparse_vector)}"
            )
        
        return sparse_vector if sparse_vector else None
    
    def get_generator(self, index_id: str) -> Optional[BM25SparseGenerator]:
        """
        获取指定索引的 BM25 生成器
        
        Args:
            index_id: 索引 ID
            
        Returns:
            BM25SparseGenerator 实例，不存在则返回 None
        """
        return self._get_generator(index_id)
    
    def _get_generator(self, index_id: str) -> Optional[BM25SparseGenerator]:
        """获取或加载 BM25 生成器"""
        # 先检查缓存
        if index_id in self._generators:
            return self._generators[index_id]
        
        # 尝试从磁盘加载
        stats_path = self._get_stats_path(index_id)
        if os.path.exists(stats_path):
            try:
                generator = BM25SparseGenerator.load_stats(stats_path)
                self._generators[index_id] = generator
                return generator
            except Exception as e:
                logger.error(f"加载 BM25 统计信息失败: {e}")
                return None
        
        return None
    
    def _get_stats_path(self, index_id: str) -> str:
        """获取 BM25 统计文件路径"""
        return os.path.join(self.stats_dir, f"{index_id}_bm25_stats.json")
    
    def has_stats(self, index_id: str) -> bool:
        """检查指定索引是否有 BM25 统计信息"""
        if index_id in self._generators:
            return True
        return os.path.exists(self._get_stats_path(index_id))
    
    def get_stats(self, index_id: str) -> Optional[Dict[str, Any]]:
        """获取指定索引的 BM25 统计摘要"""
        generator = self._get_generator(index_id)
        if generator:
            return generator.get_stats()
        return None
