"""测试专用第三方包桩：本机未安装 redis/psycopg 时让纯逻辑模块可导入。

仅满足 src.config.runtime 在导入期的引用，不提供真实连接能力。
"""


class Redis:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def from_url(cls, *args, **kwargs):
        return cls()

    def __getattr__(self, name):
        def _stub(*args, **kwargs):
            return None
        return _stub


class RedisError(Exception):
    pass
