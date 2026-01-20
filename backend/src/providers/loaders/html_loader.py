"""HTML document loader using BeautifulSoup."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if BeautifulSoup is available
BS4_AVAILABLE = False
BS4_UNAVAILABLE_REASON = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError as e:
    BS4_UNAVAILABLE_REASON = f"BeautifulSoup not installed: {str(e)}. Install with: pip install beautifulsoup4 lxml"


class HTMLLoader:
    """Load HTML documents using BeautifulSoup."""
    
    def __init__(self):
        """Initialize HTML loader."""
        self.name = "html"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from HTML document.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            Dictionary with extracted content
        """
        if not BS4_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": BS4_UNAVAILABLE_REASON
            }
        
        try:
            # Read file
            path = Path(file_path)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml' if self._has_lxml() else 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
                element.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else None
            
            # Extract headings
            headings = []
            for level in range(1, 7):
                for heading in soup.find_all(f'h{level}'):
                    headings.append({
                        'level': level,
                        'text': heading.get_text(strip=True)
                    })
            
            # Extract tables
            tables = self._extract_tables(soup)
            
            # Extract images (详细信息)
            images = self._extract_images(soup)
            
            # 生成带有图片位置标记的结构化文本（用于RAG）
            structured_text = self._extract_structured_content(soup, images)
            
            # 生成Markdown格式文本（用于预览，包含图片）
            markdown_text = self._generate_markdown_content(soup, images, title)
            
            # 纯文本（向后兼容）
            full_text = soup.get_text(separator='\n', strip=True)
            
            # Create single page with structured content
            pages = [{
                "page_number": 1,
                "text": markdown_text,  # 使用Markdown格式，支持图片预览
                "char_count": len(markdown_text),
                "headings": headings
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "title": title,
                    "format": "html",
                    "has_images": len(images) > 0,
                    "image_count": len(images)
                },
                "pages": pages,
                "tables": tables,
                "images": images,
                "full_text": markdown_text,  # 使用Markdown格式
                "structured_text": structured_text,  # RAG优化的结构化文本
                "plain_text": full_text,  # 纯文本备份
                "total_pages": 1,
                "total_chars": len(markdown_text)
            }
            
        except Exception as e:
            logger.error(f"HTML extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _extract_structured_content(self, soup, images: list) -> str:
        """
        提取结构化内容，在图片位置插入标记，便于RAG理解图文关系。
        
        输出格式示例：
        # 标题
        这是一段文字...
        
        [IMAGE_0: src="https://..." alt="图片描述" context="相关上下文"]
        
        继续的文字...
        """
        # 创建图片索引映射
        image_map = {}
        for idx, img_tag in enumerate(soup.find_all('img')):
            image_map[id(img_tag)] = idx
        
        # 递归处理DOM树，生成结构化文本
        lines = []
        self._process_element_structured(soup.body or soup, lines, image_map, images)
        
        return '\n'.join(lines)
    
    def _process_element_structured(self, element, lines: list, image_map: dict, images: list, depth: int = 0):
        """递归处理DOM元素，生成结构化文本"""
        from bs4 import NavigableString, Tag
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    lines.append(text)
            elif isinstance(child, Tag):
                tag_name = child.name
                
                # 处理标题
                if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    level = int(tag_name[1])
                    heading_text = child.get_text(strip=True)
                    if heading_text:
                        lines.append('')
                        lines.append('#' * level + ' ' + heading_text)
                        lines.append('')
                
                # 处理图片 - 插入结构化标记
                elif tag_name == 'img':
                    img_id = id(child)
                    if img_id in image_map:
                        idx = image_map[img_id]
                        img_info = images[idx] if idx < len(images) else {}
                        
                        # 构建图片标记
                        src = img_info.get('src', '')
                        alt = img_info.get('alt_text', '')
                        caption = img_info.get('caption', '')
                        context = img_info.get('context', {})
                        
                        # 生成RAG友好的图片描述
                        img_marker = f"\n[IMAGE_{idx}]"
                        img_details = []
                        if src:
                            img_details.append(f"src=\"{src}\"")
                        if alt:
                            img_details.append(f"alt=\"{alt}\"")
                        if caption:
                            img_details.append(f"caption=\"{caption}\"")
                        if context:
                            ctx_parts = []
                            if context.get('text_before'):
                                ctx_parts.append(f"前文: {context['text_before']}")
                            if context.get('text_after'):
                                ctx_parts.append(f"后文: {context['text_after']}")
                            if ctx_parts:
                                img_details.append(f"context=\"{'; '.join(ctx_parts)}\"")
                        
                        if img_details:
                            img_marker += f" ({' '.join(img_details)})"
                        
                        lines.append(img_marker)
                        lines.append('')
                
                # 处理段落
                elif tag_name == 'p':
                    text = child.get_text(strip=True)
                    if text:
                        lines.append(text)
                        lines.append('')
                
                # 处理列表
                elif tag_name in ['ul', 'ol']:
                    lines.append('')
                    for li in child.find_all('li', recursive=False):
                        li_text = li.get_text(strip=True)
                        if li_text:
                            prefix = '- ' if tag_name == 'ul' else '1. '
                            lines.append(prefix + li_text)
                    lines.append('')
                
                # 处理其他块级元素
                elif tag_name in ['div', 'section', 'article', 'main', 'aside', 'header', 'footer', 'nav']:
                    self._process_element_structured(child, lines, image_map, images, depth + 1)
                
                # 处理其他元素
                else:
                    self._process_element_structured(child, lines, image_map, images, depth)
    
    def _generate_markdown_content(self, soup, images: list, title: Optional[str] = None) -> str:
        """
        生成Markdown格式内容，包含图片的Markdown语法，用于前端预览。
        """
        lines = []
        
        # 添加标题
        if title:
            lines.append(f"# {title}")
            lines.append('')
        
        # 创建图片索引映射
        image_map = {}
        for idx, img_tag in enumerate(soup.find_all('img')):
            image_map[id(img_tag)] = idx
        
        # 递归处理DOM树
        self._process_element_markdown(soup.body or soup, lines, image_map, images)
        
        # 清理多余空行
        result = '\n'.join(lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    
    def _process_element_markdown(self, element, lines: list, image_map: dict, images: list):
        """递归处理DOM元素，生成Markdown格式文本"""
        from bs4 import NavigableString, Tag
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    lines.append(text)
            elif isinstance(child, Tag):
                tag_name = child.name
                
                # 处理标题
                if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    level = int(tag_name[1])
                    heading_text = child.get_text(strip=True)
                    if heading_text:
                        lines.append('')
                        lines.append('#' * level + ' ' + heading_text)
                        lines.append('')
                
                # 处理图片 - 生成Markdown图片语法
                elif tag_name == 'img':
                    img_id = id(child)
                    if img_id in image_map:
                        idx = image_map[img_id]
                        img_info = images[idx] if idx < len(images) else {}
                        
                        src = img_info.get('src', '')
                        alt = img_info.get('alt_text', '') or f'图片{idx + 1}'
                        caption = img_info.get('caption', '')
                        
                        if src:
                            # 生成Markdown图片语法
                            lines.append('')
                            lines.append(f'![{alt}]({src})')
                            if caption:
                                lines.append(f'*{caption}*')
                            lines.append('')
                
                # 处理段落
                elif tag_name == 'p':
                    # 检查段落内是否有图片
                    has_only_img = len(child.find_all('img')) > 0 and not child.get_text(strip=True)
                    if has_only_img:
                        # 如果段落只包含图片，递归处理
                        self._process_element_markdown(child, lines, image_map, images)
                    else:
                        text = child.get_text(strip=True)
                        if text:
                            lines.append(text)
                            lines.append('')
                
                # 处理figure（通常包含图片和标题）
                elif tag_name == 'figure':
                    self._process_element_markdown(child, lines, image_map, images)
                
                # 处理列表
                elif tag_name in ['ul', 'ol']:
                    lines.append('')
                    for li_idx, li in enumerate(child.find_all('li', recursive=False)):
                        li_text = li.get_text(strip=True)
                        if li_text:
                            prefix = '- ' if tag_name == 'ul' else f'{li_idx + 1}. '
                            lines.append(prefix + li_text)
                    lines.append('')
                
                # 处理链接
                elif tag_name == 'a':
                    href = child.get('href', '')
                    text = child.get_text(strip=True)
                    if text and href and not href.startswith('#'):
                        lines.append(f'[{text}]({href})')
                    elif text:
                        lines.append(text)
                
                # 处理强调
                elif tag_name in ['strong', 'b']:
                    text = child.get_text(strip=True)
                    if text:
                        lines.append(f'**{text}**')
                
                elif tag_name in ['em', 'i']:
                    text = child.get_text(strip=True)
                    if text:
                        lines.append(f'*{text}*')
                
                # 处理代码
                elif tag_name == 'code':
                    text = child.get_text(strip=True)
                    if text:
                        lines.append(f'`{text}`')
                
                elif tag_name == 'pre':
                    code = child.find('code')
                    if code:
                        text = code.get_text()
                        lines.append('')
                        lines.append('```')
                        lines.append(text)
                        lines.append('```')
                        lines.append('')
                
                # 处理换行
                elif tag_name == 'br':
                    lines.append('')
                
                # 处理水平线
                elif tag_name == 'hr':
                    lines.append('')
                    lines.append('---')
                    lines.append('')
                
                # 处理块级容器
                elif tag_name in ['div', 'section', 'article', 'main', 'aside', 'header', 'footer', 'nav', 'span']:
                    self._process_element_markdown(child, lines, image_map, images)
                
                # 其他元素递归处理
                else:
                    self._process_element_markdown(child, lines, image_map, images)
    
    def _extract_tables(self, soup) -> list:
        """Extract tables from HTML."""
        tables = []
        
        for idx, table in enumerate(soup.find_all('table')):
            headers = []
            rows = []
            
            # Extract headers
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text(strip=True))
            
            # Extract rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                if cells:
                    row = [cell.get_text(strip=True) for cell in cells]
                    # If no headers yet, use first row as headers
                    if not headers and len(rows) == 0:
                        headers = row
                    else:
                        rows.append(row)
            
            if headers or rows:
                tables.append({
                    "page_number": 1,
                    "table_index": idx,
                    "headers": headers,
                    "rows": rows,
                    "caption": table.find('caption').get_text(strip=True) if table.find('caption') else None,
                    "row_count": len(rows),
                    "col_count": len(headers)
                })
        
        return tables
    
    def _extract_images(self, soup) -> list:
        """Extract comprehensive image information from HTML."""
        images = []
        
        for idx, img in enumerate(soup.find_all('img')):
            # 获取图片源URL（支持多种属性）
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            
            # 获取响应式图片源
            srcset = img.get('srcset')
            srcset_list = self._parse_srcset(srcset) if srcset else None
            
            # 获取图片尺寸
            width = img.get('width')
            height = img.get('height')
            
            # 尝试从style属性提取尺寸
            style = img.get('style', '')
            if not width:
                width = self._extract_style_value(style, 'width')
            if not height:
                height = self._extract_style_value(style, 'height')
            
            # 查找图片标题/描述
            caption = self._find_image_caption(img)
            
            # 获取上下文信息
            context = self._get_image_context(img)
            
            # 检测图片类型
            image_type = self._detect_image_type(src) if src else None
            
            # 检查是否为base64内嵌图片
            is_base64 = src.startswith('data:') if src else False
            
            image_info = {
                "page_number": 1,
                "image_index": idx,
                "src": src,
                "alt_text": img.get('alt'),
                "title": img.get('title'),
                "caption": caption,
                "width": width,
                "height": height,
                "srcset": srcset_list,
                "class": ' '.join(img.get('class', [])) if img.get('class') else None,
                "id": img.get('id'),
                "image_type": image_type,
                "is_base64": is_base64,
                "loading": img.get('loading'),  # lazy/eager
                "context": context
            }
            
            # 如果是base64图片，提取mime类型
            if is_base64 and src:
                image_info["mime_type"] = self._extract_base64_mime(src)
            
            images.append(image_info)
        
        return images
    
    def _parse_srcset(self, srcset: str) -> list:
        """解析srcset属性为结构化数据"""
        if not srcset:
            return None
        
        sources = []
        for item in srcset.split(','):
            parts = item.strip().split()
            if len(parts) >= 1:
                source = {"url": parts[0]}
                if len(parts) >= 2:
                    source["descriptor"] = parts[1]  # 如 "2x" 或 "800w"
                sources.append(source)
        
        return sources if sources else None
    
    def _extract_style_value(self, style: str, property_name: str) -> Optional[str]:
        """从style属性中提取特定CSS属性值"""
        if not style:
            return None
        
        import re
        pattern = rf'{property_name}\s*:\s*([^;]+)'
        match = re.search(pattern, style, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _find_image_caption(self, img) -> Optional[str]:
        """查找图片的标题或描述"""
        # 1. 检查父级figure标签的figcaption
        figure = img.find_parent('figure')
        if figure:
            figcaption = figure.find('figcaption')
            if figcaption:
                return figcaption.get_text(strip=True)
        
        # 2. 检查title属性
        if img.get('title'):
            return img.get('title')
        
        # 3. 检查aria-label
        if img.get('aria-label'):
            return img.get('aria-label')
        
        # 4. 检查aria-describedby引用的元素
        describedby_id = img.get('aria-describedby')
        if describedby_id:
            soup = img.find_parent(['html', '[document]'])
            if soup:
                desc_element = soup.find(id=describedby_id)
                if desc_element:
                    return desc_element.get_text(strip=True)
        
        return None
    
    def _get_image_context(self, img) -> Dict[str, Any]:
        """获取图片的上下文信息"""
        context = {}
        
        # 获取父元素信息
        parent = img.parent
        if parent and parent.name:
            context["parent_tag"] = parent.name
            if parent.get('class'):
                context["parent_class"] = ' '.join(parent.get('class'))
        
        # 获取相邻文本（前后各100字符）
        # 向前查找
        prev_text = []
        for sibling in img.previous_siblings:
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text(strip=True)
            elif isinstance(sibling, str):
                text = sibling.strip()
            else:
                continue
            if text:
                prev_text.insert(0, text)
                if len(' '.join(prev_text)) > 100:
                    break
        
        # 向后查找
        next_text = []
        for sibling in img.next_siblings:
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text(strip=True)
            elif isinstance(sibling, str):
                text = sibling.strip()
            else:
                continue
            if text:
                next_text.append(text)
                if len(' '.join(next_text)) > 100:
                    break
        
        if prev_text:
            context["text_before"] = ' '.join(prev_text)[:100]
        if next_text:
            context["text_after"] = ' '.join(next_text)[:100]
        
        return context if context else None
    
    def _detect_image_type(self, src: str) -> Optional[str]:
        """检测图片类型"""
        if not src:
            return None
        
        # base64图片
        if src.startswith('data:'):
            return self._extract_base64_mime(src)
        
        # 根据扩展名判断
        src_lower = src.lower().split('?')[0]  # 移除查询参数
        
        extension_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.bmp': 'image/bmp',
            '.avif': 'image/avif'
        }
        
        for ext, mime in extension_map.items():
            if src_lower.endswith(ext):
                return mime
        
        return None
    
    def _extract_base64_mime(self, data_uri: str) -> Optional[str]:
        """从data URI中提取MIME类型"""
        if not data_uri or not data_uri.startswith('data:'):
            return None
        
        # data:image/png;base64,xxxxx
        try:
            header = data_uri.split(',')[0]
            if ';' in header:
                mime = header.split(':')[1].split(';')[0]
                return mime
        except (IndexError, ValueError):
            pass
        
        return None
    
    def _has_lxml(self) -> bool:
        """Check if lxml is available."""
        try:
            import lxml
            return True
        except ImportError:
            return False
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return BS4_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return BS4_UNAVAILABLE_REASON


# Global instance
html_loader = HTMLLoader()
