from time import perf_counter

t0 = perf_counter()

import asyncio
from functools import cache
from threading import Thread, Lock
from types import ModuleType
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, ParamSpec, TypeVar

t1 = perf_counter()
print(f"[res] Import system module: {t1 - t0:.3f}s")

T = TypeVar("T")
P = ParamSpec("P")

_import_lock = Lock()

class BackgroundObject(Generic[P, T]):
    def __init__(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._func = func
        self._thread = Thread(None, self._work, None, args, kwargs)
        self._thread.start()
        print(f"[BackgroundObject] '{func.__module__}.{func.__name__}' is running in background with {args=}, {kwargs=}")

    def __get__(self, obj, objtype=None) -> T:
        self._thread.join()
        return self._value

    def _work(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._value = self._func(*args, **kwargs)
        print(f"[BackgroundObject] '{self._func.__module__}.{self._func.__name__}' is done with {args=}, {kwargs=}")


def import_with_lock(
    name: str,
    package: Optional[str] = None
) -> ModuleType:
    from importlib import import_module
    with _import_lock:
        return import_module(name, package)


# def lazy_import(name):
#     import importlib.util
#     import sys
#     spec = importlib.util.find_spec(name)
#     if spec is None:
#         raise ImportError(f"cannot import {name}")
#     loader = importlib.util.LazyLoader(spec.loader)  # type: ignore
#     spec.loader = loader
#     module = importlib.util.module_from_spec(spec)
#     sys.modules[name] = module
#     loader.exec_module(module)
#     return module


class NBCLI:
    _SINGLETON = None

    def __new__(cls):
        if cls._SINGLETON is None:
            cls._SINGLETON = object.__new__(cls)
            cls.handlers = BackgroundObject(import_with_lock, "nb_cli.handlers", "*")
            cls.config = BackgroundObject(import_with_lock, "nb_cli.config", "*")
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


@cache
def load_module_data_raw(
    module_name: Literal["adapters", "plugins", "drivers"]
) -> List[Dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import httpx
    exceptions: List[Exception] = []
    urls = [
        f"https://v2.nonebot.dev/{module_name}.json",
        f"https://raw.fastgit.org/nonebot/nonebot2/master/website/static/{module_name}.json",
        f"https://cdn.jsdelivr.net/gh/nonebot/nonebot2/website/static/{module_name}.json",
    ]
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [executor.submit(httpx.get, url) for url in urls]

        for future in as_completed(tasks):
            try:
                resp = future.result()
                return resp.json()
            except Exception as e:
                exceptions.append(e)

    raise Exception("Download failed", exceptions)


class Data:
    _SINGLETON = None

    def __new__(cls):
        if cls._SINGLETON is None:
            cls._SINGLETON = object.__new__(cls)
            cls.drivers = BackgroundObject(asyncio.run, NBCLI().handlers.load_module_data("driver"))
            cls.adapters = BackgroundObject(asyncio.run, NBCLI().handlers.load_module_data("adapter"))
            cls.plugins = BackgroundObject(asyncio.run, NBCLI().handlers.load_module_data("plugin"))
            cls.raw_plugins = BackgroundObject(load_module_data_raw, "plugins")
        return cls._SINGLETON


def get_builtin_plugins(pypath: str):
    return asyncio.run(NBCLI().handlers.list_builtin_plugins(python_path=pypath))


def list_paginate(lst: List[T], sz: int) -> List[List[T]]:
    return [lst[st:st + sz] for st in range(0, len(lst), sz)]

t2 = perf_counter()
print(f"[res] Setup resources: {t2 - t1:.3f}s")
print(f"[res] Total: {t2 - t0:.3f}s")