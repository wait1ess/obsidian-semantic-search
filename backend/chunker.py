"""Markdown 文本分块器"""
from pathlib import Path
from typing import List, Optional
import re


class MarkdownChunker:
    """Markdown 结构感知分块器"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
        vault_path: Path = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.vault_path = vault_path

    def chunk_file(self, file_path: Path) -> List[dict]:
        """
        分块单个 Markdown 文件

        Returns:
            List of chunks with metadata:
            [
                {
                    "content": "...",
                    "metadata": {
                        "source": "relative/path/to/file.md",
                        "chunk_index": 0,
                        "heading": "主标题",
                        "file_path": "/absolute/path/to/file.md"
                    }
                },
                ...
            ]
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"读取文件失败: {file_path} - {e}")
            return []

        # 计算相对路径作为 source
        if self.vault_path and file_path.is_relative_to(self.vault_path):
            source = str(file_path.relative_to(self.vault_path))
        else:
            source = str(file_path)

        # 传入相对路径作为 source，绝对路径作为 file_path
        return self.chunk_text(content, source=source, file_path=str(file_path))
    
    def chunk_text(
        self,
        content: str,
        source: str = "",
        file_path: str = ""
    ) -> List[dict]:
        """
        分块文本内容
        
        Args:
            content: 文本内容
            source: 相对路径（用于显示）
            file_path: 绝对路径（用于跳转）
        
        Returns:
            分块列表
        """
        # 按标题分割（保留标题层级）
        sections = self._split_by_headings(content)
        
        chunks = []
        chunk_index = 0
        
        for section in sections:
            heading = section["heading"]
            text = section["content"]
            
            # 如果整个 section 小于最小块大小，合并
            if len(text) < self.min_chunk_size:
                if chunks:
                    # 合并到上一个 chunk
                    chunks[-1]["content"] += "\n\n" + text
                continue
            
            # 如果 section 太大，需要进一步分割
            if len(text) > self.chunk_size:
                sub_chunks = self._split_large_section(text)
                for sub in sub_chunks:
                    chunks.append({
                        "content": sub,
                        "metadata": {
                            "source": source,
                            "chunk_index": chunk_index,
                            "heading": heading,
                            "file_path": file_path
                        }
                    })
                    chunk_index += 1
            else:
                chunks.append({
                    "content": text,
                    "metadata": {
                        "source": source,
                        "chunk_index": chunk_index,
                        "heading": heading,
                        "file_path": file_path
                    }
                })
                chunk_index += 1
        
        return chunks
    
    def _split_by_headings(self, content: str) -> List[dict]:
        """按标题分割内容"""
        lines = content.split("\n")
        sections = []
        current_heading = ""
        current_content = []
        
        for line in lines:
            # 检测标题 (## 开头)
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if heading_match:
                # 保存当前 section
                if current_content:
                    sections.append({
                        "heading": current_heading,
                        "content": "\n".join(current_content).strip()
                    })
                
                # 开始新 section
                current_heading = heading_match.group(2).strip()
                current_content = [line]  # 保留标题
            else:
                current_content.append(line)
        
        # 保存最后一个 section
        if current_content:
            sections.append({
                "heading": current_heading,
                "content": "\n".join(current_content).strip()
            })
        
        return sections
    
    def _split_large_section(self, text: str) -> List[str]:
        """分割过大的 section"""
        # 按段落分割
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # 如果单个段落就超过限制，按句子再分割
            if len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 按句子分割
                sentences = self._split_sentences(para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) > self.chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        # 添加重叠
                        if self.chunk_overlap > 0 and chunks:
                            overlap_text = current_chunk[-self.chunk_overlap:]
                            current_chunk = overlap_text + sent
                        else:
                            current_chunk = sent
                    else:
                        current_chunk += " " + sent
            else:
                if len(current_chunk) + len(para) + 2 > self.chunk_size:
                    chunks.append(current_chunk.strip())
                    # 添加重叠
                    if self.chunk_overlap > 0:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    current_chunk += "\n\n" + para
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子（支持中英文）"""
        # 匹配中英文句子结束符
        pattern = r'(?<=[。！？.!?])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]