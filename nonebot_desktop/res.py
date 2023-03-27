import asyncio
from sqlite3 import adapters
from nb_cli.handlers.meta import load_module_data
from nb_cli.handlers.plugin import list_builtin_plugins

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

drivers = asyncio.run(load_module_data("driver"))
adapters = asyncio.run(load_module_data("adapter"))
plugins = asyncio.run(load_module_data("plugin"))


def get_builtin_plugins(pypath: str):
    return asyncio.run(list_builtin_plugins(python_path=pypath))