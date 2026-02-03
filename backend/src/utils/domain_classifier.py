"""
Domain classifier for document content analysis.

Uses TF-IDF + keyword matching for domain classification.
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import Counter
import re


@dataclass
class DomainClassificationResult:
    """Result of domain classification."""
    domain: str
    confidence: float
    all_domains: Dict[str, float]
    keywords_matched: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "confidence": self.confidence,
            "all_domains": self.all_domains,
            "keywords_matched": self.keywords_matched,
        }


class DomainClassifier:
    """
    Domain classifier for text content.
    
    Uses keyword matching and TF-IDF for classification.
    Supports domains: general, technical, legal, medical, financial, academic, news
    """
    
    # Domain definitions with keywords
    DOMAIN_KEYWORDS = {
        "technical": {
            "zh": [
                "代码", "函数", "变量", "类", "接口", "API", "数据库", "服务器",
                "算法", "编程", "开发", "软件", "系统", "架构", "部署", "测试",
                "配置", "参数", "模块", "组件", "框架", "库", "依赖", "版本",
                "调试", "日志", "错误", "异常", "性能", "优化", "缓存", "并发",
            ],
            "en": [
                "code", "function", "variable", "class", "interface", "api", "database",
                "server", "algorithm", "programming", "development", "software", "system",
                "architecture", "deploy", "test", "config", "parameter", "module",
                "component", "framework", "library", "dependency", "version", "debug",
                "log", "error", "exception", "performance", "optimize", "cache", "concurrent",
            ],
        },
        "legal": {
            "zh": [
                "合同", "条款", "协议", "法律", "法规", "权利", "义务", "责任",
                "违约", "赔偿", "仲裁", "诉讼", "判决", "证据", "当事人", "甲方",
                "乙方", "签署", "生效", "终止", "解除", "保密", "知识产权", "著作权",
            ],
            "en": [
                "contract", "clause", "agreement", "legal", "law", "regulation", "right",
                "obligation", "liability", "breach", "compensation", "arbitration",
                "litigation", "judgment", "evidence", "party", "execute", "effective",
                "terminate", "confidential", "intellectual property", "copyright",
            ],
        },
        "medical": {
            "zh": [
                "患者", "诊断", "治疗", "症状", "药物", "手术", "病历", "检查",
                "化验", "医生", "护士", "医院", "门诊", "住院", "处方", "剂量",
                "副作用", "禁忌", "病理", "临床", "康复", "护理", "疾病", "健康",
            ],
            "en": [
                "patient", "diagnosis", "treatment", "symptom", "drug", "surgery",
                "medical record", "examination", "test", "doctor", "nurse", "hospital",
                "outpatient", "inpatient", "prescription", "dosage", "side effect",
                "contraindication", "pathology", "clinical", "recovery", "care", "disease",
            ],
        },
        "financial": {
            "zh": [
                "股票", "基金", "债券", "投资", "收益", "风险", "资产", "负债",
                "利润", "亏损", "财务", "报表", "审计", "税务", "贷款", "利率",
                "汇率", "交易", "账户", "结算", "融资", "估值", "市值", "分红",
            ],
            "en": [
                "stock", "fund", "bond", "investment", "return", "risk", "asset",
                "liability", "profit", "loss", "financial", "statement", "audit",
                "tax", "loan", "interest rate", "exchange rate", "transaction",
                "account", "settlement", "financing", "valuation", "market cap", "dividend",
            ],
        },
        "academic": {
            "zh": [
                "研究", "论文", "实验", "数据", "分析", "结论", "假设", "方法",
                "理论", "模型", "样本", "变量", "统计", "显著", "相关", "引用",
                "参考文献", "摘要", "关键词", "结果", "讨论", "综述", "学术",
            ],
            "en": [
                "research", "paper", "experiment", "data", "analysis", "conclusion",
                "hypothesis", "method", "theory", "model", "sample", "variable",
                "statistic", "significant", "correlation", "citation", "reference",
                "abstract", "keyword", "result", "discussion", "review", "academic",
            ],
        },
        "news": {
            "zh": [
                "报道", "记者", "消息", "新闻", "发布", "声明", "采访", "现场",
                "事件", "发生", "据悉", "据了解", "表示", "指出", "透露", "宣布",
                "预计", "分析人士", "业内人士", "相关人士", "今日", "昨日",
            ],
            "en": [
                "report", "reporter", "news", "press", "release", "statement",
                "interview", "scene", "event", "happen", "according", "source",
                "said", "noted", "revealed", "announced", "expected", "analyst",
                "insider", "today", "yesterday", "breaking",
            ],
        },
    }
    
    # Domain display names
    DOMAIN_NAMES = {
        "general": "通用",
        "technical": "技术",
        "legal": "法律",
        "medical": "医疗",
        "financial": "金融",
        "academic": "学术",
        "news": "新闻",
    }
    
    def __init__(self, min_keyword_matches: int = 2):
        """
        Initialize domain classifier.
        
        Args:
            min_keyword_matches: Minimum keywords to match for confident classification
        """
        self.min_keyword_matches = min_keyword_matches
        
        # Build keyword sets for faster lookup
        self._keyword_sets = {}
        for domain, lang_keywords in self.DOMAIN_KEYWORDS.items():
            self._keyword_sets[domain] = set()
            for keywords in lang_keywords.values():
                self._keyword_sets[domain].update(k.lower() for k in keywords)
    
    def classify(self, text: str, language: str = "zh") -> DomainClassificationResult:
        """
        Classify the domain of text.
        
        Args:
            text: Text to classify
            language: Primary language of text (zh, en)
            
        Returns:
            DomainClassificationResult with domain and confidence
        """
        if not text or not text.strip():
            return DomainClassificationResult(
                domain="general",
                confidence=0.5,
                all_domains={"general": 0.5}
            )
        
        # Normalize text
        text_lower = text.lower()
        
        # Count keyword matches for each domain
        domain_scores = {}
        domain_matches = {}
        
        for domain, keywords_set in self._keyword_sets.items():
            matches = []
            for keyword in keywords_set:
                if keyword in text_lower:
                    matches.append(keyword)
            
            if matches:
                domain_matches[domain] = matches
                # Score based on number of unique matches
                domain_scores[domain] = len(set(matches))
        
        # If no matches, return general
        if not domain_scores:
            return DomainClassificationResult(
                domain="general",
                confidence=0.5,
                all_domains={"general": 0.5}
            )
        
        # Calculate probabilities
        total_score = sum(domain_scores.values())
        probabilities = {
            domain: score / total_score
            for domain, score in domain_scores.items()
        }
        
        # Get primary domain
        primary_domain = max(probabilities, key=probabilities.get)
        confidence = probabilities[primary_domain]
        
        # Adjust confidence based on match count
        match_count = domain_scores.get(primary_domain, 0)
        if match_count < self.min_keyword_matches:
            confidence *= 0.7  # Lower confidence for few matches
        
        # Include general as fallback
        if "general" not in probabilities:
            probabilities["general"] = 0.1
            # Renormalize
            total = sum(probabilities.values())
            probabilities = {k: v / total for k, v in probabilities.items()}
        
        return DomainClassificationResult(
            domain=primary_domain,
            confidence=min(confidence, 0.95),  # Cap at 95%
            all_domains=probabilities,
            keywords_matched=domain_matches.get(primary_domain, [])[:10]
        )
    
    def classify_batch(self, texts: List[str], language: str = "zh") -> List[DomainClassificationResult]:
        """
        Classify domains for multiple texts.
        
        Args:
            texts: List of texts to classify
            language: Primary language
            
        Returns:
            List of DomainClassificationResult
        """
        return [self.classify(text, language) for text in texts]
    
    def classify_aggregate(self, texts: List[str], language: str = "zh") -> DomainClassificationResult:
        """
        Classify aggregate domain across multiple texts.
        
        Args:
            texts: List of texts (e.g., document chunks)
            language: Primary language
            
        Returns:
            Aggregate DomainClassificationResult
        """
        if not texts:
            return DomainClassificationResult(
                domain="general",
                confidence=0.5,
                all_domains={"general": 0.5}
            )
        
        # Combine all texts for analysis
        combined_text = " ".join(texts)
        
        # Classify combined text
        return self.classify(combined_text, language)
    
    def get_domain_name(self, domain: str) -> str:
        """Get human-readable domain name."""
        return self.DOMAIN_NAMES.get(domain, domain)


# Global instance for convenience
_default_classifier = None


def classify_domain(text: str, language: str = "zh") -> DomainClassificationResult:
    """
    Classify domain of text using default classifier.
    
    Args:
        text: Text to classify
        language: Primary language
        
    Returns:
        DomainClassificationResult
    """
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = DomainClassifier()
    return _default_classifier.classify(text, language)


def classify_aggregate_domain(texts: List[str], language: str = "zh") -> DomainClassificationResult:
    """
    Classify aggregate domain across multiple texts.
    
    Args:
        texts: List of texts
        language: Primary language
        
    Returns:
        DomainClassificationResult
    """
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = DomainClassifier()
    return _default_classifier.classify_aggregate(texts, language)
