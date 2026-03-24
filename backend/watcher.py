"""文件监听服务 - 实时同步 Obsidian Vault"""
from pathlib import Path
from typing import Optional, Callable, Set
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from datetime import datetime
from collections import defaultdict

from .config import settings


class DebouncedHandler(FileSystemEventHandler):
    """防抖的文件事件处理器"""
    
    def __init__(
        self,
        callback: Callable[[Path, str], None],
        debounce_seconds: float = 2.0,
        extensions: Set[str] = None
    ):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.extensions = extensions or {".md"}
        
        # 防抖相关
        self._pending_events: dict = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
    
    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.suffix.lower() not in self.extensions:
            return
        
        self._schedule_event(path, "modified")
    
    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.suffix.lower() not in self.extensions:
            return
        
        self._schedule_event(path, "created")
    
    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.suffix.lower() not in self.extensions:
            return
        
        self._schedule_event(path, "deleted")
    
    def _schedule_event(self, path: Path, event_type: str):
        """调度事件（带防抖）"""
        with self._lock:
            # 记录最新事件
            self._pending_events[str(path)] = {
                "path": path,
                "type": event_type,
                "time": time.time()
            }
            
            # 取消之前的定时器
            if self._timer:
                self._timer.cancel()
            
            # 设置新的定时器
            self._timer = threading.Timer(
                self.debounce_seconds,
                self._process_events
            )
            self._timer.start()
    
    def _process_events(self):
        """处理累积的事件"""
        with self._lock:
            if not self._pending_events:
                return
            
            # 复制并清空
            events = dict(self._pending_events)
            self._pending_events.clear()
        
        # 处理每个事件
        for path_str, event in events.items():
            try:
                self.callback(event["path"], event["type"])
            except Exception as e:
                print(f"处理事件失败: {event['path']} - {e}")


class VaultWatcher:
    """Obsidian Vault 文件监听器"""
    
    def __init__(
        self,
        vault_path: Path,
        on_file_change: Callable[[Path, str], None],
        debounce_seconds: float = None
    ):
        self.vault_path = vault_path
        self.on_file_change = on_file_change
        self.debounce_seconds = debounce_seconds or settings.watcher_debounce_seconds
        
        self._observer: Optional[Observer] = None
        self._running = False
        self._indexed_files: Set[str] = set()
        self._event_log: list = []
    
    def start(self):
        """启动监听"""
        if self._running:
            return
        
        # 创建处理器
        handler = DebouncedHandler(
            callback=self._handle_event,
            debounce_seconds=self.debounce_seconds
        )
        
        # 创建观察者
        self._observer = Observer()
        self._observer.schedule(
            handler,
            str(self.vault_path),
            recursive=True
        )
        
        self._observer.start()
        self._running = True
        
        print(f"🔍 开始监听 Vault: {self.vault_path}")
    
    def stop(self):
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        self._running = False
        print("⏹️ 停止监听")
    
    def _handle_event(self, path: Path, event_type: str):
        """处理文件事件"""
        # 记录事件日志
        log_entry = {
            "time": datetime.now().isoformat(),
            "path": str(path.relative_to(self.vault_path)),
            "type": event_type
        }
        self._event_log.append(log_entry)
        
        # 保留最近 100 条日志
        if len(self._event_log) > 100:
            self._event_log = self._event_log[-100:]
        
        print(f"📝 [{event_type}] {path.relative_to(self.vault_path)}")
        
        # 调用回调
        self.on_file_change(path, event_type)
    
    def get_event_log(self, limit: int = 20) -> list:
        """获取事件日志"""
        return self._event_log[-limit:]
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def get_indexed_count(self) -> int:
        """获取已索引文件数"""
        return len(self._indexed_files)
    
    def mark_indexed(self, path: Path):
        """标记文件已索引"""
        self._indexed_files.add(str(path))
    
    def remove_indexed(self, path: Path):
        """移除已索引标记"""
        self._indexed_files.discard(str(path))


# 全局实例
_watcher: Optional[VaultWatcher] = None


def get_watcher() -> Optional[VaultWatcher]:
    """获取全局 Watcher 实例"""
    return _watcher


def init_watcher(
    vault_path: Path,
    on_file_change: Callable[[Path, str], None]
) -> VaultWatcher:
    """初始化 Watcher"""
    global _watcher
    _watcher = VaultWatcher(vault_path, on_file_change)
    return _watcher