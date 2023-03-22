import asyncio
from sqlite3 import adapters
from nb_cli.handlers.meta import load_module_data
from nb_cli.handlers.plugin import list_builtin_plugins

drivers = asyncio.run(load_module_data("driver"))
adapters = asyncio.run(load_module_data("adapter"))
plugins = asyncio.run(load_module_data("plugin"))