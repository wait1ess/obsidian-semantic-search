#!/usr/bin/env python3
"""全量索引脚本 - 可独立运行"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from backend.config import settings
from backend.chunker import MarkdownChunker
from backend.embedder import get_embedder
from backend.vectorstore import get_vectorstore
import time


def main():
    print("=" * 60)
    print("Obsidian Vault 全量索引")
    print("=" * 60)
    
    print(f"\nVault 路径: {settings.vault_path}")
    print(f"向量库路径: {settings.chroma_path}")
    print(f"Embedding 模型: {settings.embedding_model}")
    
    # 检查 Vault 是否存在
    if not settings.vault_path.exists():
        print(f"❌ Vault 路径不存在: {settings.vault_path}")
        sys.exit(1)
    
    # 初始化组件
    print("\n正在初始化...")
    chunker = MarkdownChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )
    
    # 预加载模型
    print("加载 Embedding 模型...")
    embedder = get_embedder()
    print(f"向量维度: {embedder.get_embedding_dim()}")
    
    store = get_vectorstore()
    
    # 扫描文件
    print("\n扫描 Markdown 文件...")
    md_files = list(settings.vault_path.rglob("*.md"))
    md_files = [f for f in md_files if ".obsidian" not in str(f)]
    
    print(f"发现 {len(md_files)} 个 Markdown 文件")
    
    # 索引
    start_time = time.time()
    total_chunks = 0
    indexed_files = 0
    errors = []
    
    for i, md_file in enumerate(md_files, 1):
        try:
            # 获取相对路径
            rel_path = str(md_file.relative_to(settings.vault_path))
            
            # 删除旧数据
            store.delete_by_source(rel_path)
            
            # 分块
            chunks = chunker.chunk_file(md_file)
            if not chunks:
                continue
            
            # 准备数据
            documents = [c["content"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            ids = [f"{rel_path}#{c['metadata']['chunk_index']}" for c in chunks]
            
            # 写入向量库
            store.upsert_documents(documents, metadatas, ids)
            
            total_chunks += len(chunks)
            indexed_files += 1
            
            # 进度
            if i % 10 == 0 or i == len(md_files):
                print(f"进度: {i}/{len(md_files)} | 已索引: {indexed_files} | Chunks: {total_chunks}")
                
        except Exception as e:
            errors.append((str(md_file), str(e)))
    
    took_seconds = time.time() - start_time
    
    # 输出结果
    print("\n" + "=" * 60)
    print("索引完成")
    print("=" * 60)
    print(f"✅ 成功索引: {indexed_files} 个文件")
    print(f"📝 创建 chunks: {total_chunks}")
    print(f"⏱️ 耗时: {took_seconds:.2f} 秒")
    
    if errors:
        print(f"\n⚠️ {len(errors)} 个文件索引失败:")
        for path, err in errors[:5]:
            print(f"  - {path}: {err}")
    
    # 统计
    stats = store.get_stats()
    print(f"\n📊 向量库统计:")
    print(f"  - 总 chunks: {stats['total_chunks']}")
    print(f"  - 总文件: {stats['total_files']}")


if __name__ == "__main__":
    main()