"""
Language detector for document content analysis.

Uses langdetect library with fallback mechanisms.
"""
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import Counter


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: str
    confidence: float
    all_languages: Dict[str, float]  # All detected languages with probabilities
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "language": self.language,
            "confidence": self.confidence,
            "all_languages": self.all_languages,
        }


class LanguageDetector:
    """
    Language detector for text content.
    
    Uses langdetect with ensemble voting for improved accuracy.
    """
    
    # Language code mapping
    LANGUAGE_NAMES = {
        "zh-cn": "中文",
        "zh-tw": "中文",
        "zh": "中文",
        "en": "英文",
        "ja": "日文",
        "ko": "韩文",
        "de": "德文",
        "fr": "法文",
        "es": "西班牙文",
        "pt": "葡萄牙文",
        "ru": "俄文",
        "ar": "阿拉伯文",
    }
    
    # Normalized language codes
    LANGUAGE_NORMALIZE = {
        "zh-cn": "zh",
        "zh-tw": "zh",
    }
    
    def __init__(self, num_samples: int = 3):
        """
        Initialize language detector.
        
        Args:
            num_samples: Number of detection samples for ensemble voting
        """
        self.num_samples = num_samples
        self._detector = None
    
    def _get_detector(self):
        """Lazy initialization of langdetect."""
        if self._detector is None:
            try:
                from langdetect import detect_langs, DetectorFactory
                # Set seed for reproducibility
                DetectorFactory.seed = 42
                self._detector = detect_langs
            except ImportError:
                raise ImportError(
                    "langdetect is required for language detection. "
                    "Install with: pip install langdetect"
                )
        return self._detector
    
    def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detect the primary language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageDetectionResult with primary language and confidence
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                all_languages={}
            )
        
        # Clean text
        text = self._clean_text(text)
        
        if len(text) < 10:
            return self._detect_short_text(text)
        
        try:
            detect_langs = self._get_detector()
            
            # Use ensemble voting for better accuracy
            all_detections = []
            for _ in range(self.num_samples):
                try:
                    langs = detect_langs(text)
                    for lang in langs:
                        normalized = self._normalize_language(lang.lang)
                        all_detections.append((normalized, lang.prob))
                except Exception:
                    continue
            
            if not all_detections:
                return self._fallback_detection(text)
            
            # Aggregate results
            lang_probs = {}
            for lang, prob in all_detections:
                if lang not in lang_probs:
                    lang_probs[lang] = []
                lang_probs[lang].append(prob)
            
            # Calculate average probabilities
            avg_probs = {
                lang: sum(probs) / len(probs)
                for lang, probs in lang_probs.items()
            }
            
            # Get primary language
            primary_lang = max(avg_probs, key=avg_probs.get)
            confidence = avg_probs[primary_lang]
            
            return LanguageDetectionResult(
                language=primary_lang,
                confidence=confidence,
                all_languages=avg_probs
            )
            
        except Exception as e:
            # Fallback to heuristic detection
            return self._fallback_detection(text)
    
    def detect_batch(self, texts: List[str]) -> List[LanguageDetectionResult]:
        """
        Detect languages for multiple texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of LanguageDetectionResult
        """
        return [self.detect(text) for text in texts]
    
    def detect_aggregate(self, texts: List[str]) -> LanguageDetectionResult:
        """
        Detect aggregate language across multiple texts.
        
        Useful for determining primary language of a document
        from multiple chunks.
        
        Args:
            texts: List of texts (e.g., document chunks)
            
        Returns:
            Aggregate LanguageDetectionResult
        """
        if not texts:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                all_languages={}
            )
        
        # Detect each text
        results = self.detect_batch(texts)
        
        # Aggregate results weighted by confidence
        lang_weights = {}
        for result in results:
            for lang, prob in result.all_languages.items():
                if lang not in lang_weights:
                    lang_weights[lang] = 0
                lang_weights[lang] += prob
        
        if not lang_weights:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                all_languages={}
            )
        
        # Normalize weights
        total_weight = sum(lang_weights.values())
        normalized = {
            lang: weight / total_weight
            for lang, weight in lang_weights.items()
        }
        
        primary_lang = max(normalized, key=normalized.get)
        
        return LanguageDetectionResult(
            language=primary_lang,
            confidence=normalized[primary_lang],
            all_languages=normalized
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean text for detection."""
        import re
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove code-like content
        text = re.sub(r'[{}\[\]()<>]', ' ', text)
        # Remove excessive whitespace
        text = ' '.join(text.split())
        return text
    
    def _normalize_language(self, lang: str) -> str:
        """Normalize language code."""
        lang_lower = lang.lower()
        return self.LANGUAGE_NORMALIZE.get(lang_lower, lang_lower)
    
    def _detect_short_text(self, text: str) -> LanguageDetectionResult:
        """Detect language for short text using character analysis."""
        # Count character types
        chinese = 0
        japanese = 0
        korean = 0
        latin = 0
        
        for char in text:
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:  # CJK Unified Ideographs
                chinese += 1
            elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:  # Hiragana/Katakana
                japanese += 1
            elif 0xAC00 <= code <= 0xD7AF:  # Hangul
                korean += 1
            elif 0x0041 <= code <= 0x007A:  # Latin
                latin += 1
        
        total = chinese + japanese + korean + latin
        if total == 0:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                all_languages={}
            )
        
        probs = {
            "zh": chinese / total if chinese > 0 else 0,
            "ja": (japanese + chinese * 0.3) / total if japanese > 0 else 0,
            "ko": korean / total if korean > 0 else 0,
            "en": latin / total if latin > 0 else 0,
        }
        
        # Remove zero probabilities
        probs = {k: v for k, v in probs.items() if v > 0}
        
        if not probs:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                all_languages={}
            )
        
        primary = max(probs, key=probs.get)
        
        return LanguageDetectionResult(
            language=primary,
            confidence=probs[primary],
            all_languages=probs
        )
    
    def _fallback_detection(self, text: str) -> LanguageDetectionResult:
        """Fallback detection using character analysis."""
        return self._detect_short_text(text)
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name."""
        return self.LANGUAGE_NAMES.get(code.lower(), code)


# Global instance for convenience
_default_detector = None


def detect_language(text: str) -> LanguageDetectionResult:
    """
    Detect language of text using default detector.
    
    Args:
        text: Text to analyze
        
    Returns:
        LanguageDetectionResult
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = LanguageDetector()
    return _default_detector.detect(text)


def detect_aggregate_language(texts: List[str]) -> LanguageDetectionResult:
    """
    Detect aggregate language across multiple texts.
    
    Args:
        texts: List of texts to analyze
        
    Returns:
        LanguageDetectionResult
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = LanguageDetector()
    return _default_detector.detect_aggregate(texts)
