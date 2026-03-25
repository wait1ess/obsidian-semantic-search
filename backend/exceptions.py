"""自定义异常类"""


class ObsidianRAGError(Exception):
    """基础异常类"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict:
        result = {"error": self.message}
        if self.details:
            result["details"] = self.details
        return result


class IndexingError(ObsidianRAGError):
    """索引相关错误"""
    pass


class FileNotFoundError(ObsidianRAGError):
    """文件未找到错误"""
    pass


class VaultNotFoundError(ObsidianRAGError):
    """Vault 路径不存在错误"""
    pass


class ModelLoadError(ObsidianRAGError):
    """模型加载错误"""
    pass


class VectorStoreError(ObsidianRAGError):
    """向量存储错误"""
    pass


class CacheError(ObsidianRAGError):
    """缓存相关错误"""
    pass


class SearchError(ObsidianRAGError):
    """搜索相关错误"""
    pass


class IndexAlreadyRunningError(ObsidianRAGError):
    """索引任务已在运行"""
    pass