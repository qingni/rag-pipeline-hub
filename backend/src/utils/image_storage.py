"""图片混合存储策略工具类。

提供统一的图片存储策略，支持：
- 大图(>阈值): 保存为文件，仅存储路径，按需加载
- 小图(<=阈值): 直接存储 base64，便于快速访问
- 缩略图生成: 用于前端快速预览

所有 loader 应使用此工具类来处理图片存储，确保策略一致性。
"""
import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ImageStorageConfig:
    """图片存储配置。
    
    Attributes:
        size_threshold: 大小阈值（字节），超过此大小保存为文件，默认 50KB
        thumbnail_max_size: 缩略图最大边长，默认 200 像素
        generate_thumbnail: 是否生成缩略图，默认 True
    """
    size_threshold: int = 50 * 1024  # 50KB
    thumbnail_max_size: int = 200
    generate_thumbnail: bool = True


# 默认全局配置
DEFAULT_CONFIG = ImageStorageConfig()


class ImageStorageManager:
    """图片混合存储管理器。
    
    使用混合存储策略处理图片：
    - 大图保存为文件，返回文件路径
    - 小图保留 base64，直接内联
    - 可选生成缩略图用于预览
    """
    
    def __init__(self, config: Optional[ImageStorageConfig] = None):
        """初始化存储管理器。
        
        Args:
            config: 存储配置，默认使用全局配置
        """
        self.config = config or DEFAULT_CONFIG
    
    @staticmethod
    def generate_thumbnail(image_bytes: bytes, max_size: int = 200) -> Optional[str]:
        """生成缩略图的 base64 编码。
        
        Args:
            image_bytes: 原始图片字节数据
            max_size: 缩略图最大边长
            
        Returns:
            缩略图的 base64 编码字符串，失败返回 None
        """
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(image_bytes))
            
            # 保持宽高比缩放
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 转换为 RGB（处理 RGBA 或其他模式）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 保存为 JPEG 格式（压缩率高）
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=75)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.debug(f"生成缩略图失败: {e}")
            return None
    
    @staticmethod
    def get_image_dimensions(image_bytes: bytes) -> Tuple[Optional[int], Optional[int]]:
        """获取图片尺寸。
        
        Args:
            image_bytes: 图片字节数据
            
        Returns:
            (width, height) 元组，失败返回 (None, None)
        """
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(image_bytes))
            return img.size
        except Exception:
            return None, None
    
    @staticmethod
    def detect_mime_type(image_bytes: bytes) -> str:
        """检测图片 MIME 类型。
        
        Args:
            image_bytes: 图片字节数据
            
        Returns:
            MIME 类型字符串，默认 'image/png'
        """
        # 根据文件头魔数检测
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        elif image_bytes[:2] == b'\xff\xd8':
            return 'image/jpeg'
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif'
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return 'image/webp'
        elif image_bytes[:2] in (b'BM',):
            return 'image/bmp'
        elif image_bytes[:4] in (b'II*\x00', b'MM\x00*'):
            return 'image/tiff'
        else:
            return 'image/png'  # 默认
    
    @staticmethod
    def get_extension_from_mime(mime_type: str) -> str:
        """根据 MIME 类型获取文件扩展名。
        
        Args:
            mime_type: MIME 类型
            
        Returns:
            文件扩展名（不含点）
        """
        ext_map = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp',
            'image/tiff': 'tiff',
        }
        return ext_map.get(mime_type, 'png')
    
    def process_image(
        self,
        image_bytes: bytes,
        image_index: int,
        figures_dir: Optional[Path] = None,
        doc_id: Optional[str] = None,
        page_number: int = 1,
        mime_type: Optional[str] = None,
        force_inline: bool = False,
        force_file: bool = False,
    ) -> Dict[str, Any]:
        """处理图片，根据混合存储策略决定存储方式。
        
        Args:
            image_bytes: 图片字节数据
            image_index: 图片在文档中的索引
            figures_dir: 图片保存目录（用于大图存储）
            doc_id: 文档 ID（用于文件命名）
            page_number: 页码
            mime_type: MIME 类型，不提供则自动检测
            force_inline: 强制内联存储（忽略大小阈值）
            force_file: 强制文件存储（忽略大小阈值）
            
        Returns:
            包含存储结果的字典：
            {
                "file_path": str or None,  # 大图文件路径
                "base64_data": str or None,  # 小图 base64 数据
                "thumbnail_base64": str or None,  # 缩略图
                "mime_type": str,
                "original_size": int,
                "width": int or None,
                "height": int or None,
                "storage_type": "inline" or "file",  # 存储类型标识
            }
        """
        image_size = len(image_bytes)
        
        # 检测或使用提供的 MIME 类型
        if not mime_type:
            mime_type = self.detect_mime_type(image_bytes)
        
        # 获取图片尺寸
        width, height = self.get_image_dimensions(image_bytes)
        
        result = {
            "file_path": None,
            "base64_data": None,
            "thumbnail_base64": None,
            "mime_type": mime_type,
            "original_size": image_size,
            "width": width,
            "height": height,
            "storage_type": None,
        }
        
        # 决定存储方式
        use_file_storage = False
        
        if force_file:
            use_file_storage = True
        elif force_inline:
            use_file_storage = False
        else:
            # 根据阈值判断
            use_file_storage = image_size > self.config.size_threshold
        
        if use_file_storage and figures_dir:
            # 大图：保存为文件
            ext = self.get_extension_from_mime(mime_type)
            
            # 构建文件路径
            if doc_id:
                doc_figures_dir = figures_dir / doc_id
            else:
                doc_figures_dir = figures_dir
            
            doc_figures_dir.mkdir(parents=True, exist_ok=True)
            
            # 文件命名：page_imageIndex.ext
            filename = f"img_{page_number}_{image_index}.{ext}"
            file_path = doc_figures_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            result["file_path"] = str(file_path)
            result["storage_type"] = "file"
            
            # 为大图生成缩略图
            if self.config.generate_thumbnail:
                result["thumbnail_base64"] = self.generate_thumbnail(
                    image_bytes, self.config.thumbnail_max_size
                )
            
            logger.debug(
                f"[大图存储] 图片 {image_index} ({image_size} bytes) 保存到 {file_path}"
            )
        else:
            # 小图：内联 base64
            result["base64_data"] = base64.b64encode(image_bytes).decode('utf-8')
            result["storage_type"] = "inline"
            
            logger.debug(
                f"[小图内联] 图片 {image_index} ({image_size} bytes) 内联存储"
            )
        
        return result
    
    def process_base64_image(
        self,
        base64_data: str,
        image_index: int,
        figures_dir: Optional[Path] = None,
        doc_id: Optional[str] = None,
        page_number: int = 1,
        mime_type: Optional[str] = None,
        force_inline: bool = False,
        force_file: bool = False,
    ) -> Dict[str, Any]:
        """处理 base64 编码的图片。
        
        Args:
            base64_data: base64 编码的图片数据（不含 data:image/xxx;base64, 前缀）
            其他参数同 process_image
            
        Returns:
            同 process_image
        """
        try:
            image_bytes = base64.b64decode(base64_data)
            return self.process_image(
                image_bytes=image_bytes,
                image_index=image_index,
                figures_dir=figures_dir,
                doc_id=doc_id,
                page_number=page_number,
                mime_type=mime_type,
                force_inline=force_inline,
                force_file=force_file,
            )
        except Exception as e:
            logger.warning(f"处理 base64 图片失败: {e}")
            return {
                "file_path": None,
                "base64_data": None,
                "thumbnail_base64": None,
                "mime_type": mime_type,
                "original_size": 0,
                "width": None,
                "height": None,
                "storage_type": "error",
                "error": str(e),
            }
    
    def load_image_for_embedding(
        self,
        file_path: Optional[str] = None,
        base64_data: Optional[str] = None,
    ) -> Optional[str]:
        """获取用于多模态嵌入的图片 base64 数据。
        
        优先使用内联 base64，否则从文件按需加载。
        
        Args:
            file_path: 图片文件路径
            base64_data: 已有的 base64 数据
            
        Returns:
            base64 编码的图片数据，失败返回 None
        """
        if base64_data:
            return base64_data
        
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                logger.warning(f"按需加载图片失败 {file_path}: {e}")
        
        return None


# 全局单例实例
_default_manager: Optional[ImageStorageManager] = None


def get_image_storage_manager(config: Optional[ImageStorageConfig] = None) -> ImageStorageManager:
    """获取图片存储管理器实例。
    
    Args:
        config: 自定义配置，不提供则使用默认配置
        
    Returns:
        ImageStorageManager 实例
    """
    global _default_manager
    
    if config:
        return ImageStorageManager(config)
    
    if _default_manager is None:
        _default_manager = ImageStorageManager()
    
    return _default_manager


# 便捷函数，直接使用默认配置
def process_image(
    image_bytes: bytes,
    image_index: int,
    figures_dir: Optional[Path] = None,
    doc_id: Optional[str] = None,
    page_number: int = 1,
    mime_type: Optional[str] = None,
    force_inline: bool = False,
    force_file: bool = False,
) -> Dict[str, Any]:
    """处理图片（使用默认配置）。
    
    参数和返回值同 ImageStorageManager.process_image
    """
    return get_image_storage_manager().process_image(
        image_bytes=image_bytes,
        image_index=image_index,
        figures_dir=figures_dir,
        doc_id=doc_id,
        page_number=page_number,
        mime_type=mime_type,
        force_inline=force_inline,
        force_file=force_file,
    )


def process_base64_image(
    base64_data: str,
    image_index: int,
    figures_dir: Optional[Path] = None,
    doc_id: Optional[str] = None,
    page_number: int = 1,
    mime_type: Optional[str] = None,
    force_inline: bool = False,
    force_file: bool = False,
) -> Dict[str, Any]:
    """处理 base64 图片（使用默认配置）。
    
    参数和返回值同 ImageStorageManager.process_base64_image
    """
    return get_image_storage_manager().process_base64_image(
        base64_data=base64_data,
        image_index=image_index,
        figures_dir=figures_dir,
        doc_id=doc_id,
        page_number=page_number,
        mime_type=mime_type,
        force_inline=force_inline,
        force_file=force_file,
    )
