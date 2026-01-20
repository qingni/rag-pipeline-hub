"""Unstructured document loader with multimodal support.

支持从文档中提取文本和图片，为多模态嵌入模型 (qwen3-vl-embedding-8b) 提供数据支持。
"""
import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class UnstructuredLoader:
    """Load documents using Unstructured library with multimodal support.
    
    支持:
    - 文本提取 (所有支持格式)
    - 图片提取和保存 (PDF, DOCX 等)
    - 表格结构识别
    - OCR 文字识别
    """
    
    # 默认图片保存目录 (相对于工作目录)
    DEFAULT_FIGURES_DIR = "figures"
    
    def __init__(self, figures_dir: Optional[str] = None):
        """Initialize Unstructured loader.
        
        Args:
            figures_dir: 图片保存目录，默认为 'figures'
        """
        self.name = "unstructured"
        self._unavailable_reason = None
        self.figures_dir = figures_dir or self.DEFAULT_FIGURES_DIR
    
    def is_available(self) -> bool:
        """Check if Unstructured library is available."""
        try:
            from unstructured.partition.auto import partition
            self._unavailable_reason = None
            return True
        except ImportError as e:
            self._unavailable_reason = f"Unstructured library not installed: {str(e)}"
            return False
    
    def get_unavailable_reason(self) -> str:
        """Get reason why loader is unavailable."""
        return self._unavailable_reason or "Unknown reason"
    
    def extract_text(
        self, 
        file_path: str,
        extract_images: bool = True,
        save_images: bool = True,
        embed_images_base64: bool = False
    ) -> Dict[str, Any]:
        """Extract text and images from document using Unstructured.
        
        Args:
            file_path: Path to document file
            extract_images: 是否提取图片信息
            save_images: 是否将图片保存为文件
            embed_images_base64: 是否将图片嵌入为 Base64 (用于多模态处理)
            
        Returns:
            Dictionary with extracted content and metadata, including:
            - pages: 分页文本内容
            - images: 图片信息列表 (支持多模态)
            - tables: 表格信息列表
        """
        try:
            from unstructured.partition.auto import partition
            from unstructured.documents.elements import Image as UnstructuredImage
            
            path = Path(file_path)
            doc_id = self._generate_doc_id(path)
            
            # 确保图片目录存在
            figures_path = Path(self.figures_dir)
            if save_images and not figures_path.exists():
                figures_path.mkdir(parents=True, exist_ok=True)
            
            # Partition document with full extraction options
            elements = partition(
                filename=file_path,
                strategy="hi_res",
                extract_images_in_pdf=extract_images,
                infer_table_structure=True,
                ocr_languages="chi_sim+eng",
                extract_image_block_to_payload=True,  # 提取图片到 payload
                extract_image_block_types=["Image", "Figure"],  # 提取的图片类型
            )
            
            # Process elements
            pages_text: Dict[int, List[str]] = {}
            full_text: List[str] = []
            images: List[Dict[str, Any]] = []
            tables: List[Dict[str, Any]] = []
            
            image_index = 0
            prev_text = ""  # 跟踪上一个文本元素，用于图片上下文
            
            for i, element in enumerate(elements):
                page_num = getattr(element.metadata, 'page_number', 1) if hasattr(element, 'metadata') else 1
                element_type = type(element).__name__
                
                if page_num not in pages_text:
                    pages_text[page_num] = []
                
                # 处理图片元素
                if element_type in ('Image', 'Figure') and extract_images:
                    image_info = self._process_image_element(
                        element=element,
                        image_index=image_index,
                        page_num=page_num,
                        doc_id=doc_id,
                        figures_path=figures_path,
                        save_images=save_images,
                        embed_base64=embed_images_base64,
                        context_before=prev_text[-200:] if prev_text else None  # 保留最后200字符作为上下文
                    )
                    if image_info:
                        images.append(image_info)
                        # 在文本中插入图片占位符
                        placeholder = f"[IMAGE_{image_index}: {image_info.get('caption') or '图片'}]"
                        pages_text[page_num].append(placeholder)
                        full_text.append(placeholder)
                        image_index += 1
                
                # 处理表格元素
                elif element_type == 'Table':
                    table_info = self._process_table_element(element, page_num, len(tables))
                    if table_info:
                        tables.append(table_info)
                        # 表格文本也加入
                        table_text = element.text
                        pages_text[page_num].append(table_text)
                        full_text.append(table_text)
                        prev_text = table_text
                
                # 处理普通文本元素
                else:
                    text = element.text
                    if text:
                        pages_text[page_num].append(text)
                        full_text.append(text)
                        prev_text = text
                        
                        # 更新上一个图片的 context_after
                        if images and not images[-1].get('context_after'):
                            images[-1]['context_after'] = text[:200]  # 前200字符
            
            # Format pages
            pages = []
            for page_num in sorted(pages_text.keys()):
                text = "\n".join(pages_text[page_num])
                pages.append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text)
                })
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "elements_count": len(elements),
                    "image_count": len(images),
                    "table_count": len(tables),
                    "multimodal_ready": len(images) > 0  # 标记是否有多模态内容
                },
                "pages": pages,
                "images": images,
                "tables": tables,
                "full_text": "\n\n".join(full_text),
                "total_pages": len(pages),
                "total_chars": sum(p["char_count"] for p in pages)
            }
            
        except ImportError as e:
            return {
                "success": False,
                "loader": self.name,
                "error": f"Unstructured dependency missing: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Document extraction failed: {e}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _process_image_element(
        self,
        element,
        image_index: int,
        page_num: int,
        doc_id: str,
        figures_path: Path,
        save_images: bool,
        embed_base64: bool,
        context_before: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Process an image element and extract multimodal data.
        
        Args:
            element: Unstructured Image/Figure element
            image_index: 图片序号
            page_num: 页码
            doc_id: 文档 ID
            figures_path: 图片保存目录
            save_images: 是否保存图片文件
            embed_base64: 是否嵌入 Base64
            context_before: 图片前的文本上下文
        
        Returns:
            图片信息字典，支持多模态处理
        """
        try:
            metadata = element.metadata if hasattr(element, 'metadata') else None
            
            # 基础信息
            image_info = {
                "page_number": page_num,
                "image_index": image_index,
                "caption": None,
                "alt_text": None,
                "bbox": None,
                "file_path": None,
                "base64_data": None,
                "mime_type": None,
                "width": None,
                "height": None,
                "context_before": context_before,
                "context_after": None,
                "image_type": "figure",
                "ocr_text": None
            }
            
            # 提取元数据
            if metadata:
                # 标题/描述
                image_info["caption"] = getattr(metadata, 'image_caption', None)
                image_info["alt_text"] = getattr(metadata, 'alt_text', None) or element.text
                
                # 位置信息
                coords = getattr(metadata, 'coordinates', None)
                if coords:
                    image_info["bbox"] = {
                        "x1": coords.points[0][0] if coords.points else 0,
                        "y1": coords.points[0][1] if coords.points else 0,
                        "x2": coords.points[2][0] if len(coords.points) > 2 else 0,
                        "y2": coords.points[2][1] if len(coords.points) > 2 else 0
                    }
                
                # 图片数据 (从 payload 提取)
                image_base64 = getattr(metadata, 'image_base64', None)
                if not image_base64:
                    # 尝试从其他属性获取
                    image_base64 = getattr(metadata, 'image', None)
                
                if image_base64:
                    # 检测图片格式
                    mime_type = self._detect_image_mime(image_base64)
                    image_info["mime_type"] = mime_type
                    
                    # 保存图片文件
                    if save_images:
                        ext = mime_type.split('/')[-1] if mime_type else 'png'
                        filename = f"{doc_id}-{page_num}-{image_index}.{ext}"
                        file_path = figures_path / filename
                        
                        try:
                            # 解码并保存
                            image_data = base64.b64decode(image_base64)
                            with open(file_path, 'wb') as f:
                                f.write(image_data)
                            image_info["file_path"] = str(file_path)
                            
                            # 获取图片尺寸
                            size = self._get_image_size(image_data)
                            if size:
                                image_info["width"], image_info["height"] = size
                                
                            logger.debug(f"Saved image: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to save image: {e}")
                    
                    # 嵌入 Base64
                    if embed_base64:
                        image_info["base64_data"] = image_base64
                
                # OCR 文字
                ocr_text = getattr(metadata, 'text_as_html', None) or getattr(metadata, 'ocr_text', None)
                if ocr_text:
                    image_info["ocr_text"] = ocr_text
            
            # 如果没有任何有用信息，跳过
            if not any([
                image_info["file_path"],
                image_info["base64_data"],
                image_info["caption"],
                image_info["alt_text"],
                image_info["ocr_text"]
            ]):
                return None
            
            return image_info
            
        except Exception as e:
            logger.warning(f"Failed to process image element: {e}")
            return None
    
    def _process_table_element(
        self,
        element,
        page_num: int,
        table_index: int
    ) -> Optional[Dict[str, Any]]:
        """Process a table element."""
        try:
            metadata = element.metadata if hasattr(element, 'metadata') else None
            
            table_info = {
                "page_number": page_num,
                "table_index": table_index,
                "headers": [],
                "rows": [],
                "caption": None,
                "markdown": element.text,
                "html": None
            }
            
            if metadata:
                # 尝试获取结构化表格数据
                text_as_html = getattr(metadata, 'text_as_html', None)
                if text_as_html:
                    table_info["html"] = text_as_html
            
            return table_info
            
        except Exception as e:
            logger.warning(f"Failed to process table element: {e}")
            return None
    
    def _generate_doc_id(self, path: Path) -> str:
        """Generate a short document ID from file path."""
        name = path.stem
        # 取文件名前20个字符 + hash 后4位
        hash_suffix = hashlib.md5(str(path).encode()).hexdigest()[:4]
        return f"{name[:20]}_{hash_suffix}"
    
    def _detect_image_mime(self, base64_data: str) -> str:
        """Detect image MIME type from Base64 data."""
        try:
            # 解码前几个字节来检测格式
            data = base64.b64decode(base64_data[:32] + '==')
            
            if data[:8] == b'\x89PNG\r\n\x1a\n':
                return 'image/png'
            elif data[:2] == b'\xff\xd8':
                return 'image/jpeg'
            elif data[:6] in (b'GIF87a', b'GIF89a'):
                return 'image/gif'
            elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
                return 'image/webp'
            else:
                return 'image/png'  # 默认
        except:
            return 'image/png'
    
    def _get_image_size(self, image_data: bytes) -> Optional[Tuple[int, int]]:
        """Get image dimensions from binary data."""
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_data))
            return img.size
        except:
            return None


# Global instance
unstructured_loader = UnstructuredLoader()
