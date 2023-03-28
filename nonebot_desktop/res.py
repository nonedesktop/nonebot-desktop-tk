import asyncio
from importlib import import_module
from threading import Thread
from typing import Callable, Generic, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


class BackgroundObject(Generic[P, T]):
    def __init__(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._func = func
        self._thread = Thread(None, self._work, None, args, kwargs)
        self._thread.start()

    def __get__(self, obj, objtype=None) -> T:
        self._thread.join()
        return self._value

    def _work(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._value = self._func(*args, **kwargs)


class NBCLI:
    _SINGLETON = None

    def __new__(cls):
        if cls._SINGLETON is None:
            cls._SINGLETON = object.__new__(cls)
            cls.load_module_data = BackgroundObject(import_module, "load_module_data", "nb_cli.handlers.meta")
            cls.list_builtin_plugins = BackgroundObject(import_module, "list_builtin_plugins", "nb_cli.handlers.plugin")
            cls.create_project = BackgroundObject(import_module, "create_project", "nb_cli.handlers.project")
        return cls._SINGLETON


PYPI_MIRRORS = [
    "https://pypi.org/simple",
    "https://pypi.doubanio.com/simple",
    "https://mirrors.163.com/pypi/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.bfsu.edu.cn/pypi/web/simple",
    "https://mirrors.sustech.edu.cn/pypi/simple"
]


class Data:
    _SINGLETON = None

    def __new__(cls):
        if cls._SINGLETON is None:
            cls._SINGLETON = object.__new__(cls)
            cls.drivers = BackgroundObject(asyncio.run, NBCLI().load_module_data("driver"))
            cls.adapters = BackgroundObject(asyncio.run, NBCLI().load_module_data("adapter"))
            cls.plugins = BackgroundObject(asyncio.run, NBCLI().load_module_data("plugin"))
        return cls._SINGLETON


def get_builtin_plugins(pypath: str):
    return asyncio.run(NBCLI().list_builtin_plugins(python_path=pypath))