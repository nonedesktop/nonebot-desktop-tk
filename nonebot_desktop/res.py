import asyncio
import importlib.util
import sys
from threading import Thread, Lock
from types import ModuleType
from typing import Callable, Generic, Mapping, ParamSpec, Sequence, TypeVar

T = TypeVar("T")
P = ParamSpec("P")

_import_lock = Lock()

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


def import_with_lock(
    name: str,
    globals: Mapping[str, object] | None = None,
    locals: Mapping[str, object] | None = None,
    fromlist: Sequence[str] = ...,
    level: int = 0
) -> ModuleType:
    with _import_lock:
        return __import__(name, globals, locals, fromlist, level)


def lazy_import(name):
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise ImportError(f"cannot import {name}")
    loader = importlib.util.LazyLoader(spec.loader)  # type: ignore
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


class NBCLI:
    _SINGLETON = None

    def __new__(cls):
        if cls._SINGLETON is None:
            cls._SINGLETON = object.__new__(cls)
            cls.meta = BackgroundObject(import_with_lock, "nb_cli.handlers.meta")
            cls.parser = BackgroundObject(import_with_lock, "nb_cli.config.parser")
            cls.plugin = BackgroundObject(import_with_lock, "nb_cli.handlers.plugin")
            cls.project = BackgroundObject(import_with_lock, "nb_cli.handlers.project")
        return cls._SINGLETON


# meta = lazy_import("nb_cli.handlers.meta")
# plugin = lazy_import("nb_cli.handlers.plugin")
# project = lazy_import("nb_cli.handlers.project")


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
            cls.drivers = BackgroundObject(asyncio.run, NBCLI().meta.load_module_data("driver"))
            cls.adapters = BackgroundObject(asyncio.run, NBCLI().meta.load_module_data("adapter"))
            cls.plugins = BackgroundObject(asyncio.run, NBCLI().meta.load_module_data("plugin"))
        return cls._SINGLETON


def get_builtin_plugins(pypath: str):
    return asyncio.run(NBCLI().plugin.list_builtin_plugins(python_path=pypath))