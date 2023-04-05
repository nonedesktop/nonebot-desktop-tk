from types import ModuleType
from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, ParamSpec, Sequence, Type, TypeVar
import nb_cli.handlers
import nb_cli.config
from nb_cli.config import Driver, Plugin, Adapter

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


# def lazy_import(name: str) -> ModuleType:
#     ...


class NBCLI:
    _SINGLETON: Optional[NBCLI]

    def __new__(cls) -> NBCLI:
        ...

    class handlers:
        @staticmethod
        def create_project(
            project_template: str,
            context: Optional[Dict[str, Any]] = None,
            output_dir: Optional[str] = None,
            no_input: bool = True,
        ) -> None:
            ...

    class config:
        ConfigManager: Type[nb_cli.config.ConfigManager]
        SimpleInfo: Type[nb_cli.config.SimpleInfo]


RawPlugin = dict[
    {
        "module_name": str,
        "project_link": str,
        "name": str,
        "desc": str,
        "author": str,
        "homepage": str,
        "tags": List[dict[{"label": str, "color": str}]],
        "is_official": bool
    }
]


class Data:
    _SINGLETON: Optional[Data]

    def __new__(cls) -> Data:
        ...

    drivers: List[Driver]
    adapters: List[Adapter]
    plugins: List[Plugin]
    raw_plugins: List[RawPlugin]


def get_builtin_plugins(pypath: str) -> List[str]:
    ...


def list_paginate(lst: List[T], sz: int) -> List[List[T]]:
    ...