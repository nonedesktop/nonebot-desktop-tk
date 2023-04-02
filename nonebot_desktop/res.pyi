from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, ParamSpec, Sequence, TypeVar
import nb_cli.handlers.meta
import nb_cli.config.parser
import nb_cli.handlers.plugin
import nb_cli.handlers.project
from nb_cli.config import Driver, Plugin, Adapter, NoneBotConfig, SimpleInfo
from tomlkit import TOMLDocument

T = TypeVar("T")
P = ParamSpec("P")

PYPI_MIRRORS: List[str]


class BackgroundObject(Generic[P, T]):
    def __init__(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        ...

    def __get__(self, obj, objtype=None) -> T:
        ...

    def _work(self, *args: P.args, **kwargs: P.kwargs) -> None:
        ...


def import_with_lock(
    name: str,
    globals: Mapping[str, object] | None = None,
    locals: Mapping[str, object] | None = None,
    fromlist: Sequence[str] = ...,
    level: int = 0
) -> ModuleType:
    ...


def lazy_import(name: str) -> ModuleType:
    ...


class NBCLI:
    _SINGLETON: Optional[NBCLI]

    def __new__(cls) -> NBCLI:
        ...

    meta: ModuleType = nb_cli.handlers.meta
    # parser: ModuleType = nb_cli.config.parser

    class parser:
        class ConfigManager:
            def __init__(
                self,
                python: Optional[str] = None,
                config_file: Path = Path("pyproject.toml"),
                encoding: str = "utf-8",
            ):
                self.python = python
                self.file = config_file
                self.encoding = encoding

            def _get_data(self) -> Optional[TOMLDocument]:
                ...

            def _write_data(self, data: TOMLDocument) -> None:
                ...

            def _get_nonebot_config(self, data: TOMLDocument) -> Dict[str, Any]:
                ...

            def get_nonebot_config(self) -> NoneBotConfig:
                ...

            def add_adapter(self, adapter: SimpleInfo) -> None:
                ...

            def remove_adapter(self, adapter: SimpleInfo) -> None:
                ...

            def add_plugin(self, plugin: str) -> None:
                ...

            def remove_plugin(self, plugin: str) -> None:
                ...

            def add_builtin_plugin(self, plugin: str) -> None:
                ...

            def remove_builtin_plugin(self, plugin: str) -> None:
                ...

    plugin: ModuleType = nb_cli.handlers.plugin

    # project: ModuleType = nb_cli.handlers.project

    class project:
        @staticmethod
        def create_project(
            project_template: str,
            context: Optional[Dict[str, Any]] = None,
            output_dir: Optional[str] = None,
            no_input: bool = True,
        ) -> None:
            ...


class Data:
    _SINGLETON: Optional[Data]

    def __new__(cls) -> Data:
        ...

    drivers: List[Driver]
    adapters: List[Adapter]
    plugins: List[Plugin]


def get_builtin_plugins(pypath: str) -> List[str]:
    ...