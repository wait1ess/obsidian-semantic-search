#!/usr/bin/env python3
"""重置向量库脚本"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.vectorstore import get_vectorstore


def main():
    print("⚠️ 即将清空向量库...")
    confirm = input("确认继续? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("已取消")
        return
    
    store = get_vectorstore()
    store.reset()
    
    print("✅ 向量库已重置")


if __name__ == "__main__":
    main()