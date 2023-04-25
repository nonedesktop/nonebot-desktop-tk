import time

t0 = time.perf_counter()

from functools import partial
import os
from pathlib import Path
from subprocess import Popen
import sys
from threading import Thread, Timer
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, cast

t1 = time.perf_counter()
print(f"[GUI] Import base: {t1 - t0:.3f}s")

import tkinter as tk
from tkinter import BooleanVar, Event, IntVar, TclError, filedialog, messagebox, StringVar
from tkinter import ttk

t1_1 = time.perf_counter()
print(f"[GUI] Import tkinter: {t1_1 - t1:.3f}s")

from nonebot_desktop_wing import (
    PYPI_MIRRORS, meta, create, rrggbb_bg2fg, getdist, find_python,
    recursive_find_env_config, recursive_update_env_config, molecules,
    exec_new_win, open_new_win, system_open, get_toml_config, lazylib,
    get_builtin_plugins, find_env_file, list_paginate
)

t1_2 = time.perf_counter()
print(f"[GUI] Import this module: {t1_2 - t1_1:.3f}s")

from tkreform import Packer, Widget
from tkreform.base import Application
from tkreform.declarative import M, W, Gridder, MenuBinder, NotebookAdder
from tkreform.menu import MenuCascade, MenuCommand, MenuSeparator
from tkreform.events import LMB, X2
from dotenv.main import DotEnv

t2 = time.perf_counter()
print(f"[GUI] Import rest modules: {t2 - t1_2:.3f}s")

if TYPE_CHECKING:
    from importlib.metadata import Distribution

font10 = ("Microsoft Yahei UI", 10)
mono10 = ("Consolas", 10)


class Context:
    def __init__(self, main: "MainApp") -> None:
        self.main = main
        self.cwd = StringVar(value="[点击“项目”菜单新建或打开项目]")
        self.tmpindex = StringVar()
        self.curproc: Optional[Popen[bytes]] = None
        self.curdists: List["Distribution"] = []
        self.distvar = StringVar()
        self.cwd.trace_add("write", self.cwd_updator)

    @property
    def cwd_str(self) -> str:
        return self.cwd.get()

    @cwd_str.setter
    def cwd_str(self, dir: str) -> None:
        self.cwd.set(dir)

    @property
    def cwd_path(self) -> Path:
        return Path(self.cwd_str)

    @property
    def tmp_index(self) -> str:
        return self.tmpindex.get()

    def upddists(self) -> None:
        self.curdists = list(getdist(self.cwd_str))
        self.curdistnames = [d.metadata["name"].lower() for d in self.curdists]
        self.distvar.set(self.curdistnames)  # type: ignore
        print("[upddists] Updated current dists")

    @property
    def cwd_valid(self) -> bool:
        return (
            self.cwd_path.is_dir()
            and (
                (self.cwd_path / "pyproject.toml").is_file()
                or (self.cwd_path / "bot.py").is_file()
            )
        )

    def cwd_updator(self, *_) -> None:
        valid = self.cwd_valid
        self.main.win[1][1].disabled = not valid
        m: tk.Menu = self.main.win[0].base  # type: ignore
        for entry in (2, 3, 4):
            m.entryconfig(entry, state="normal" if valid else "disabled")
        if valid:
            Thread(target=self.upddists).start()
            print(f"[cwd_updator] Current directory is set to {self.cwd_str!r}")

    def check_pyproject_toml(self) -> None:
        if (self.cwd_path / "bot.py").exists():
            if (self.cwd_path / "pyproject.toml").exists():
                messagebox.showwarning("警告", "检测到目录下存在 bot.py，其可能不会使用 pyproject.toml 中的配置项。", master=self.main.win.base)
            else:
                messagebox.showerror("错误", "当前目录下没有 pyproject.toml，无法修改配置。", master=self.main.win.base)
                raise Exception("当前目录下没有 pyproject.toml，无法修改配置。")

    @property
    def curdist_dict(self):
        return {dist.name: dist for dist in self.curdists}


class ApplicationWithContext(Application):
    def __init__(self, base, context: Context) -> None:
        self.context = context
        super().__init__(base)


class MainApp(Application):
    def setup(self) -> None:
        self.win.title = "NoneBot Desktop"
        self.win.size = 452, 80
        self.win.resizable = False

        self.context = Context(self)

        self.win /= (
            W(tk.Menu) * MenuBinder(self.win) / (
                M(MenuCascade(label="项目", font=font10), tearoff=False) * MenuBinder() / (
                    MenuCommand(label="新建项目", font=font10, command=lambda: CreateProject(self.win.sub_window(), self.context)),
                    MenuCommand(label="打开项目", font=font10, command=self.open_project),
                    MenuCommand(label="启动项目", font=font10, command=self.start),
                    MenuSeparator(),
                    MenuCommand(label="打开项目文件夹", font=font10, command=self.open_pdir),
                    MenuSeparator(),
                    MenuCommand(label="退出", font=font10, command=self.win.destroy, accelerator="Alt+F4")
                ),
                M(MenuCascade(label="配置", font=font10), tearoff=False) * MenuBinder() / (
                    MenuCommand(label="配置文件编辑器", command=lambda: DotenvEditor(self.win.sub_window(), self.context), font=font10),
                    MenuSeparator(),
                    MenuCommand(label="管理驱动器", command=lambda: DriverManager(self.win.sub_window(), self.context), font=font10),
                    MenuCommand(label="管理适配器", command=lambda: AdapterManager(self.win.sub_window(), self.context), font=font10),
                    MenuSeparator(),
                    MenuCommand(label="管理环境", command=lambda: EnvironmentManager(self.win.sub_window(), self.context), font=font10)
                ),
                M(MenuCascade(label="插件", font=font10), tearoff=False) * MenuBinder() / (
                    MenuCommand(label="管理内置插件", command=lambda: BuiltinPlugins(self.win.sub_window(), self.context), font=font10),
                    MenuCommand(label="插件商店", command=lambda: PluginStore(self.win.sub_window(), self.context), font=font10),
                ),
                M(MenuCascade(label="高级", font=font10), tearoff=False) * MenuBinder() / (
                    MenuCommand(label="打开命令行窗口", font=font10, command=lambda: open_new_win(self.context.cwd_path)),
                    MenuSeparator(),
                    MenuCommand(label="编辑 pyproject.toml", font=font10, command=lambda: system_open(self.context.cwd_path / "pyproject.toml"))
                ),
                M(MenuCascade(label="帮助", font=font10), tearoff=False) * MenuBinder() / (
                    MenuCommand(label="使用手册", command=lambda: AppHelp(self.win.sub_window()), font=font10),
                    MenuCommand(label="关于", command=lambda: AppAbout(self.win.sub_window()), font=font10)
                )
            ),
            W(tk.Frame) * Gridder() / (
                W(tk.Frame) * Gridder() / (
                    W(tk.Label, text="当前路径：", font=("Microsoft Yahei UI", 12)) * Packer(side="left"),
                    W(tk.Entry, textvariable=self.context.cwd, font=("Microsoft Yahei UI", 12), width=40) * Packer(side="left", expand=True)
                ),
                W(tk.Button, text="启动", command=self.start, font=("Microsoft Yahei UI", 20)) * Gridder(row=1, sticky="w")
            )
        )

        self.context.cwd_updator()

    def run(self) -> None:
        self.win.loop()

    def open_project(self) -> None:
        self.context.cwd_str = filedialog.askdirectory(mustexist=True, parent=self.win.base, title="选择项目目录")

    def start(self) -> None:
        if not self.context.cwd_valid:
            messagebox.showerror("错误", "当前目录不是正确的项目目录。", master=self.win.base)
            return
        self.win[1][0][1].disabled = True
        self.win[1][1].disabled = True
        curproc, tmp = exec_new_win(
            f'''"{sys.executable}" -m nb_cli run''',
            cwd=self.context.cwd_str
        )

        def _restore():
            try:
                while curproc.poll() is None:
                    pass
            except Exception as e:
                messagebox.showerror("错误", f"{e}", master=self.win.base)
            finally:
                os.remove(tmp)
                self.win[1][0][1].disabled = False
                self.win[1][1].disabled = False

        Thread(target=_restore).start()

    def open_pdir(self) -> None:
        if not self.context.cwd_valid:
            messagebox.showerror("错误", "当前目录不是正确的项目目录。", master=self.win.base)
            return
        system_open(self.context.cwd_str)


class CreateProject(ApplicationWithContext):
    def setup(self) -> None:
        self.win.title = "NoneBot Desktop - 新建项目"
        self.win.base.grab_set()
        self.create_target = StringVar()
        self.driver_select_state = [BooleanVar(value=d.name == "FastAPI") for d in meta.drivers]
        self.adapter_select_state = [BooleanVar(value=False) for _ in meta.adapters]
        self.dev_mode = BooleanVar(value=False)
        self.use_venv = BooleanVar(value=True)

        self.win /= (
            W(tk.Frame) * Packer(fill="x", expand=True, padx=2, pady=2) / (
                W(tk.Label, text="项目目录：", font=font10) * Packer(side="left"),
                W(tk.Entry, textvariable=self.create_target, font=font10) * Packer(side="left", expand=True, fill="x"),
                W(tk.Button, text="浏览……", font=font10, command=self.ct_browse) * Packer(side="left")
            ),
            W(tk.LabelFrame, text="驱动器", font=font10) * Packer(fill="x", expand=True) / (
                W(tk.Checkbutton, text=f"{dr.name} ({dr.desc})", variable=dv, font=font10) * Packer(side="top", anchor="w")
                for dr, dv in zip(meta.drivers, self.driver_select_state)
            ),
            W(tk.LabelFrame, text="适配器", font=font10) * Packer(fill="x", expand=True) / (
                W(tk.Checkbutton, text=f"{ad.name} ({ad.desc})", variable=av, font=font10) * Packer(side="top", anchor="w")
                for ad, av in zip(meta.adapters, self.adapter_select_state)
            ),
            W(tk.Frame) * Packer(fill="x", expand=True) / (
                W(tk.Checkbutton, text="预留配置用于开发插件（将会创建 src/plugins）", variable=self.dev_mode, font=font10) * Packer(anchor="w"),
                W(tk.Checkbutton, text="创建虚拟环境（位于 .venv，用于隔离环境）", variable=self.use_venv, font=font10) * Packer(anchor="w"),
            ),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(fill="x", expand=True) / (
                W(ttk.Combobox, textvariable=self.context.tmpindex, value=PYPI_MIRRORS, font=mono10, width=50) * Packer(side="left", fill="x", expand=True),
            ),
            W(tk.Frame) * Packer(fill="x", expand=True)
        )

        self.create_btn = self.win[5].add_widget(tk.Button, text="创建", font=font10)
        self.create_btn *= Packer(side="right")
        self.create_btn.disabled = True
        self.create_btn.callback(lambda: Thread(target=self.perform_create).start())

        self.create_target.trace_add("write", self.ct_checker)

    @property
    def ct_str(self) -> str:
        return self.create_target.get()
    
    @ct_str.setter
    def ct_str(self, val: str) -> None:
        self.create_target.set(val)

    @property
    def ct_path(self) -> Path:
        return Path(self.ct_str)

    def ct_checker(self, *_) -> None:
        # For valid target:
        # - target is a path
        # - target does not exist or is empty dir
        _state = True
        if not self.ct_str:  # empty path
            messagebox.showerror("错误", "路径不能为空", master=self.win.base)
        elif self.ct_path.is_dir() and tuple(self.ct_path.iterdir()):  # non-empty dir
            messagebox.showerror("错误", "目标目录不能非空", master=self.win.base)
        elif self.ct_path.is_file():  # not dir
            messagebox.showerror("错误", "目标不能为文件", master=self.win.base)
        elif self.ct_path.stem == "nonebot":  # reserved name
            messagebox.showerror("错误", "目标目录不能使用保留名", master=self.win.base)
        else:
            _state = False
        self.create_btn.disabled = _state

    def ct_browse(self) -> None:
        self.ct_str = filedialog.askdirectory(parent=self.win.base, title="选择项目目录")

    def perform_create(self) -> None:
        drivs = [d for d, b in zip(meta.drivers, self.driver_select_state) if b.get()]
        adaps = [a for a, b in zip(meta.adapters, self.adapter_select_state) if b.get()]
        if not drivs:
            messagebox.showerror("错误", "NoneBot2 项目需要*至少一个*驱动器才能正常工作！", master=self.win.base)
            return
        if not adaps:
            messagebox.showerror("错误", "NoneBot2 项目需要*至少一个*适配器才能正常工作！", master=self.win.base)
            return
        self.create_btn.text = "正在创建项目……"
        self.create_btn.disabled = True
        try:
            create(
                self.ct_str, drivs, adaps, self.dev_mode.get(), self.use_venv.get(),
                self.context.tmp_index, new_win=True
            )
        except Exception as e:
            messagebox.showerror("错误", f"{e}", master=self.win.base)
            return
        self.context.cwd_str = self.ct_str
        try:
            self.win.destroy()
        except TclError:
            pass
        messagebox.showinfo(title="项目创建完成", message="项目创建成功，已自动进入该项目。", master=self.context.main.win.base)


class DriverManager(ApplicationWithContext):
    def setup(self) -> None:
        self.drv_installed_states = [StringVar(value="安装") for _ in meta.drivers]  # drivers' states (installed, not installed)
        self.drv_enabled_states = [StringVar(value="启用") for _ in meta.drivers]  # drivers' states (enabled, disabled)
        self.win.title = "NoneBot Desktop - 管理驱动器"
        self.win.resizable = False
        self.win.base.grab_set()

        self.win /= (
            W(tk.Frame) * Packer(side="top") / (
                (
                    W(tk.LabelFrame, text=drv.name, font=font10) * Gridder(column=n & 1, row=n // 2, sticky="nw") / (
                        W(tk.Label, text=drv.desc, font=font10, width=20, height=3, justify="left") * Packer(anchor="nw", side="top"),
                        W(tk.Frame) * Packer(anchor="nw", fill="x", side="top", expand=True) / (
                            W(tk.Button, font=font10, textvariable=self.drv_enabled_states[n], command=partial(self.perform_enable, n)) * Packer(fill="x", side="left", expand=True),
                            W(tk.Button, font=font10, textvariable=self.drv_installed_states[n], command=partial(self.perform_install, n)) * Packer(fill="x", side="left", expand=True)
                        )
                    )
                ) for n, drv in enumerate(meta.drivers)
            ),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="top", expand=True) / (
                W(ttk.Combobox, textvariable=self.context.tmpindex, value=PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
            )
        )

        self.driver_st_updator()

    def driver_st_updator(self) -> None:
        _enabled = recursive_find_env_config(self.context.cwd_str, "DRIVER")
        if _enabled is None:
            enabled = []
        else:
            enabled = _enabled.split("+")

        for n, d in enumerate(meta.drivers):
            self.drv_enabled_states[n].set("禁用" if d.module_name in enabled else "启用")
            if d.name.lower() in self.context.curdistnames:
                self.drv_installed_states[n].set("已安装")
                self.win[0][n][1][0].disabled = False
                self.win[0][n][1][1].disabled = True
            elif d.name != "None":
                self.drv_installed_states[n].set("安装")
                self.win[0][n][1][0].disabled = self.drv_enabled_states[n].get() == "禁用"
                self.win[0][n][1][1].disabled = False
            else:
                self.drv_installed_states[n].set("内置")
                self.win[0][n][1][0].disabled = False
                self.win[0][n][1][1].disabled = True

    def perform_enable(self, n: int) -> None:
        target = meta.drivers[n]
        _enabled = recursive_find_env_config(self.context.cwd_str, "DRIVER")
        if _enabled is None:
            enabled = []
        else:
            enabled = _enabled.split("+")

        if target.module_name in enabled:
            enabled.remove(target.module_name)
        else:
            enabled.append(target.module_name)

        recursive_update_env_config(self.context.cwd_str, "DRIVER", "+".join(enabled))
        self.context.upddists()
        self.driver_st_updator()

    def perform_install(self, n: int) -> None:
        target = meta.drivers[n]
        cfp = self.context.cwd_path
        self.win[0][n][1][1].disabled = True

        p, tmp = molecules.perform_pip_install(
            str(find_python(cfp)),
            target.project_link,
            index=self.context.tmp_index,
            new_win=True
        )

        def _restore():
            try:
                while p.poll() is None:
                    pass
            except Exception as e:
                messagebox.showerror("错误", f"{e}", master=self.win.base)
            finally:
                os.remove(tmp)
                self.context.upddists()
                self.driver_st_updator()

        Thread(target=_restore).start()


class AdapterManager(ApplicationWithContext):
    def setup(self) -> None:
        self.context.check_pyproject_toml()
        self.adp_installed_state = [StringVar(value="安装") for _ in meta.adapters]  # adapters' states (installed, not installed)
        self.adp_enabled_state = [StringVar(value="启用") for _ in meta.adapters]  # adapters' states (enabled, disabled)
        self.win.title = "NoneBot Desktop - 管理适配器"
        self.win.resizable = False
        self.win.base.grab_set()

        self.win /= (
            W(tk.Frame) * Packer(side="top") / (
                (
                    W(tk.LabelFrame, text=adp.name, font=font10) * Gridder(column=n % 3, row=n // 3, sticky="nw") / (
                        W(tk.Label, text=adp.desc, font=font10, width=40, height=3, justify="left") * Packer(anchor="nw", side="top"),
                        W(tk.Frame) * Packer(anchor="nw", fill="x", side="top", expand=True) / (
                            W(tk.Button, font=font10, textvariable=self.adp_enabled_state[n], command=partial(self.perform_enable, n)) * Packer(fill="x", side="left", expand=True),
                            W(tk.Button, font=font10, textvariable=self.adp_installed_state[n], command=partial(self.perform_install, n)) * Packer(fill="x", side="left", expand=True)
                        )
                    )
                ) for n, adp in enumerate(meta.adapters)
            ),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="top", expand=True) / (
                W(ttk.Combobox, textvariable=self.context.tmpindex, value=PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
            )
        )

        self.adapter_st_updator()

    def adapter_st_updator(self) -> None:
        conf = get_toml_config(self.context.cwd_str)
        if not (data := conf._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        _enabled: List[Dict[str, str]] = table.setdefault("adapters", [])
        enabled = [a["module_name"] for a in _enabled]

        for n, d in enumerate(meta.adapters):
            installed_ = d.project_link in self.context.curdistnames
            enabled_ = d.module_name in enabled
            self.adp_installed_state[n].set("卸载" if installed_ else "安装")
            self.win[0][n][1][0].disabled = not (enabled_ or installed_)
            self.adp_enabled_state[n].set("禁用" if enabled_ else "启用")
            self.win[0][n][1][1].disabled = enabled_

    def perform_enable(self, n: int) -> None:
        target = meta.adapters[n]
        slimtarget = lazylib.nb_cli.config.SimpleInfo.parse_obj(target)
        conf = get_toml_config(self.context.cwd_str)
        if self.adp_enabled_state[n].get() == "禁用":
            conf.remove_adapter(slimtarget)
        else:
            conf.add_adapter(slimtarget)
        self.adapter_st_updator()

    def perform_install(self, n: int) -> None:
        target = meta.adapters[n]
        cfp = Path(self.context.cwd_str)
        self.win[0][n][1][1].disabled = True

        p, tmp = (
            molecules.perform_pip_install(
                str(find_python(cfp)),
                target.project_link,
                index=self.context.tmp_index,
                new_win=True
            ) if self.adp_installed_state[n].get() == "安装" else
            molecules.perform_pip_command(
                str(find_python(cfp)),
                "uninstall", target.project_link,
                new_win=True
            )
        )

        def _restore():
            try:
                while p.poll() is None:
                    pass
            except Exception as e:
                messagebox.showerror("错误", f"{e}", master=self.win.base)
            finally:
                os.remove(tmp)
                self.context.upddists()
                self.adapter_st_updator()

        Thread(target=_restore).start()


class BuiltinPlugins(ApplicationWithContext):
    def setup(self) -> None:
        self.context.check_pyproject_toml()
        self.win.title = "NoneBot Desktop - 管理内置插件"
        self.win.base.grab_set()
        self.builtin_plugins = get_builtin_plugins(str(find_python(self.context.cwd_str)))
        self.bp_enabled_states = [StringVar(value="启用") for _ in self.builtin_plugins]

        self.win /= (
            (
                W(tk.Frame) * Packer(anchor="nw", fill="x", side="top") / (
                    W(tk.Label, text=bp, font=font10, justify="left") * Packer(anchor="w", expand=True, fill="x", side="left"),
                    W(tk.Button, textvariable=self.bp_enabled_states[n], command=partial(self.setnstate, n), font=font10) * Packer(anchor="w", side="left")
                )
            ) for n, bp in enumerate(self.builtin_plugins)
        )

        self.updstate()

    def updstate(self) -> None:
        cfg = get_toml_config(self.context.cwd_str)
        if not (data := cfg._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        plugins: List[str] = table.setdefault("builtin_plugins", [])
        for n, pl in enumerate(self.builtin_plugins):
            self.bp_enabled_states[n].set("禁用" if pl in plugins else "启用")

    def setnstate(self, n: int) -> None:
        cfg = get_toml_config(self.context.cwd_str)
        if self.bp_enabled_states[n].get() == "启用":
            cfg.add_builtin_plugin(self.builtin_plugins[n])
        else:
            cfg.remove_builtin_plugin(self.builtin_plugins[n])
        self.updstate()


class EnvironmentManager(ApplicationWithContext):
    def setup(self) -> None:
        self.win.title = "NoneBot Desktop - 管理环境"
        self.win.size = 720, 460
        self.win.base.grab_set()
        self.curpkg: str = ""

        self.win /= (
            W(tk.PanedWindow, showhandle=True) * Packer(fill="both", expand=True) / (
                W(tk.LabelFrame, text="程序包", font=font10) / (
                    W(tk.Listbox, listvariable=self.context.distvar, font=mono10) * Packer(side="left", fill="both", expand=True),
                    W(ttk.Scrollbar) * Packer(side="right", fill="y")
                ),
                W(tk.LabelFrame, text="详细信息", font=font10) / (
                    W(tk.Label, text="双击程序包以查看信息", font=font10, justify="left", wraplength=400) * Packer(anchor="nw", expand=True),
                    W(tk.Frame) * Packer(side="bottom", fill="x") / (
                        W(tk.Button, text="更新", command=self.perform_upgrade, font=font10, state="disabled") * Packer(side="left", fill="x", expand=True),
                        W(tk.Button, text="卸载", command=self.perform_uninstall, font=font10, state="disabled") * Packer(side="right", fill="x", expand=True)
                    ),
                    W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="bottom", expand=True) / (
                        W(ttk.Combobox, textvariable=self.context.tmpindex, value=PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
                    )
                )
            ),
        )

        li = cast(tk.Listbox, self.win[0][0][0].base)
        sl = cast(ttk.Scrollbar, self.win[0][0][1].base)
        li.config(yscrollcommand=sl.set)
        sl.config(command=li.yview)

        @self.win[0][0][0].on(str(LMB - X2))
        def showinfo(event: Event):
            self.curpkg = event.widget.get(event.widget.curselection())
            self.info_updator()

    def info_updator(self) -> None:
        if m := self.context.curdist_dict.get(self.curpkg, None):
            dm = m.metadata
            self.win[0][1][0].text = (
                f"名称：{dm['name']}\n"
                f"版本：{dm['version']}\n"
                f"摘要：{dm['summary']}\n"
            )
        else:
            self.win[0][1][0].text = "双击程序包以查看信息"

        self.win[0][1][1][0].disabled = not m
        self.win[0][1][1][1].disabled = not m

    def lock_when_perform(self, lock: bool = True) -> None:
        self.win[0][0][0].disabled = lock
        self.win[0][1][2][0].disabled = lock

    def restore_after_perform(self, popen, tmpfile) -> None:
        try:
            while popen.poll() is None:
                pass
        except Exception as e:
            messagebox.showerror("错误", f"{e}", master=self.win.base)
        finally:
            os.remove(tmpfile)
            self.context.upddists()
            self.lock_when_perform(False)
            self.info_updator()

    def perform_upgrade(self) -> None:
        self.lock_when_perform(True)
        self.win[0][1][1][0].disabled = True
        self.win[0][1][1][1].disabled = True

        p, tmp = molecules.perform_pip_install(
            str(find_python(self.context.cwd_str)),
            self.curpkg,
            update=True,
            index=self.context.tmp_index,
            new_win=True
        )

        Thread(target=self.restore_after_perform, args=(p, tmp)).start()

    def perform_uninstall(self) -> None:
        self.lock_when_perform(True)
        self.win[0][1][1][0].disabled = True
        self.win[0][1][1][1].disabled = True

        p, tmp = molecules.perform_pip_command(
            str(find_python(self.context.cwd_str)),
            "uninstall", self.curpkg, new_win=True
        )

        Thread(target=self.restore_after_perform, args=(p, tmp)).start()


class DotenvEditor(ApplicationWithContext):
    def setup(self) -> None:
        self.win.title = "NoneBot Desktop - 配置文件编辑器"
        self.win.base.grab_set()
        self.allenvs = find_env_file(self.context.cwd_str)
        self.target = StringVar(value="[请选择一个配置文件进行编辑]")
        self.curenv = DotEnv(self.target_name)
        self.curopts: List[Tuple[StringVar, StringVar]] = []

        self.win /= (
            W(tk.LabelFrame, text="可用配置文件", font=font10) * Packer(anchor="nw", fill="x", expand=True) / (
                W(ttk.Combobox, font=font10, textvariable=self.target, value=self.allenvs, width=50) * Packer(fill="x", expand=True, side="left"),
                W(tk.Button, text="新建", font=font10, command=self.create_env, state="disabled") * Packer(side="left")
            ),
            W(tk.LabelFrame, text="配置项", font=font10) * Packer(anchor="nw", fill="both", expand=True),
            W(tk.Frame) * Packer(anchor="sw", fill="x", expand=True) / (
                W(tk.Button, text="新建配置项", font=font10, command=self.new_option) * Packer(side="left"),
                W(tk.Button, text="保存", font=font10, command=self.save_env) * Packer(side="right"),
            )
        )

        self.save_btn = cast(Widget[tk.Button], self.win[2][1])

        self.target.trace_add("write", self.envf_updator)
        self.envf_updator()

    @property
    def target_name(self) -> str:
        return self.target.get()

    def envf_updator(self, *_) -> None:
        invalid = self.target_name not in self.allenvs
        self.win[2][0].disabled = invalid
        self.save_btn.disabled = invalid
        self.win[0][1].disabled = not invalid
        if invalid:
            return
        self.curenv = DotEnv(self.context.cwd_path / self.target_name)
        self.curopts = [(StringVar(value=k), StringVar(value=v)) for k, v in self.curenv.dict().items() if v is not None]
        self.win[1] /= (
            W(tk.Frame) * Packer(fill="x", expand=True) / (
                W(tk.Entry, textvariable=k, font=mono10) * Packer(side="left"),
                W(tk.Label, text=" = ", font=mono10) * Packer(side="left"),
                W(tk.Entry, textvariable=v, font=mono10) * Packer(fill="x", expand=True, side="left")
            ) for k, v in self.curopts
        )

    def create_env(self):
        self.allenvs.append(self.target_name)
        self.win[0][0].base["value"] = self.allenvs
        self.envf_updator()

    def new_option(self) -> None:
        k, v = StringVar(value="参数名"), StringVar(value="值")
        self.curopts.append((k, v))
        _row = self.win[1].add_widget(tk.Frame)
        _row.grid(column=0, sticky="w")
        _key = _row.add_widget(tk.Entry, textvariable=k, font=mono10)
        _lbl = _row.add_widget(tk.Label, text=" = ", font=mono10)
        _val = _row.add_widget(tk.Entry, textvariable=v, font=mono10, width=40)
        _key.pack(side="left")
        _lbl.pack(side="left")
        _val.pack(side="left")

    def save_env(self):
        try:
            with open(self.context.cwd_path / self.target_name, "w") as f:
                f.writelines(f"{k}={v}\n" for k, v in ((_k.get(), _v.get()) for _k, _v in self.curopts) if k and v)
        except Exception as e:
            messagebox.showerror("错误", f"{e}", master=self.win.base)
            return

        def _success():
            try:
                self.save_btn.text = "已保存"
                time.sleep(3)
                self.save_btn.text = "保存"
            except TclError:
                pass

        self.envf_updator()
        Thread(target=_success).start()


class PluginStore(ApplicationWithContext):
    PAGESIZE = 8
    sortmethods: Dict[str, Callable[[list], list]] = {
        "发布时间（旧-新）": lambda x: x,
        "发布时间（新-旧）": lambda x: list(reversed(x)),
        "模块名（A-Z）": lambda x: sorted(x, key=lambda p: p["module_name"]),
    }

    def setup(self) -> None:
        self.context.check_pyproject_toml()
        self.win.title = "NoneBot Desktop - 插件商店"
        self.win.base.grab_set()
        self.all_plugins = meta.raw_plugins
        self.all_plugins_paged = self.cur_plugins_paged = list_paginate(self.all_plugins, self.PAGESIZE)
        self.pageinfo_cpage = IntVar(value=1)
        self.pageinfo_mpage = len(self.cur_plugins_paged)
        self.pluginvars_i = [StringVar(value="安装") for _ in range(self.PAGESIZE)]
        self.pluginvars_e = [StringVar(value="启用") for _ in range(self.PAGESIZE)]

        self.searchvar = StringVar(value="")
        self.search_timer = Timer(0.8, lambda: None)

        self.sortvar = StringVar(value="发布时间（旧-新）")

        self.win /= (
            W(tk.Frame) * Packer(anchor="nw", expand=True, fill="x") / (
                W(tk.LabelFrame, text="搜索", font=font10) * Packer(anchor="nw", expand=True, fill="x", side="left") / (
                    W(tk.Entry, textvariable=self.searchvar, font=font10) * Packer(expand=True, fill="x"),
                ),
                W(tk.LabelFrame, text="排序", font=font10) * Packer(anchor="nw", side="left") / (
                    W(ttk.Combobox, textvariable=self.sortvar, value=list(self.sortmethods.keys()), font=font10) * Packer(expand=True, fill="x"),
                ),
            ),
            W(tk.LabelFrame, text=self._getrealpageinfo(), font=font10) * Packer(anchor="nw", expand=True, fill="x"),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", expand=True) / (
                W(ttk.Combobox, textvariable=self.context.tmpindex, value=PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
            ),
            W(tk.Frame) * Packer(anchor="sw", expand=True, fill="x") / (
                W(tk.Button, text="首页", font=font10, command=lambda: self.gotopage(0)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
                W(tk.Button, text="上一页", font=font10, command=lambda: self.chpage(-1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
                W(ttk.Combobox, textvariable=self.pageinfo_cpage, width=8, font=("Microsoft Yahei UI", 14)) * Packer(anchor="nw", side="left"),
                W(tk.Button, text="下一页", font=font10, command=lambda: self.chpage(1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
                W(tk.Button, text="尾页", font=font10, command=lambda: self.gotopage(-1)) * Packer(anchor="nw", expand=True, fill="x", side="left")
            )
        )

        self.pageinfo_cpage.trace_add("write", self.changepageno)
        self.sortvar.trace_add("write", self.do_search)
        self.searchvar.trace_add("write", self.applysearch)

        self.update_page()
        self.updpageinfo()

    def changepageno(self, *_):
        self.win[1].text = self._getrealpageinfo()
        self.update_page()

    def _pluginwidget(self, n: int):
        return self.win[1][n][1]

    def updpluginvars(self):
        try:
            cpage = self.pageinfo_cpage.get()
        except TclError:
            return
        curpage = self.cur_plugins_paged[cpage - 1] if self.cur_plugins_paged else []
        conf = get_toml_config(self.context.cwd_str)
        if not (data := conf._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        _enabled: List[str] = table.setdefault("plugins", [])
        enabled = [a for a in _enabled]

        for n, d in enumerate(curpage):
            installed_ = d["project_link"] in self.context.curdistnames
            enabled_ = d["module_name"] in enabled
            self.pluginvars_i[n].set("卸载" if installed_ else "安装")
            self.pluginvars_e[n].set("禁用" if enabled_ else "启用")
            self._pluginwidget(n)[1].disabled = not (enabled_ or installed_)
            self._pluginwidget(n)[2].disabled = enabled_

    def _getrealpageinfo(self) -> str:
        try:
            cpage = self.pageinfo_cpage.get()
            return f"第 {cpage}/{self.pageinfo_mpage} 页"
        except TclError:
            return self.win[1].text

    def updpageinfo(self):
        self.pageinfo_cpage.set(1)
        self.pageinfo_mpage = len(self.cur_plugins_paged)
        self.win[3][2].base["values"] = list(range(1, self.pageinfo_mpage + 1))

    def plugin_context(self, pl):
        return (
            "{name} {project_link} {module_name} {author} ".format(**pl) +
            " ".join(tag["label"] for tag in pl["tags"])
        ).lower()

    def chpage(self, offset: int):
        if self.pageinfo_mpage:
            self.pageinfo_cpage.set((self.pageinfo_cpage.get() - 1 + offset) % self.pageinfo_mpage + 1)
        else:
            self.pageinfo_cpage.set(0)

    def gotopage(self, page: int):
        if self.pageinfo_mpage:
            self.pageinfo_cpage.set(page % self.pageinfo_mpage + 1)
        else:
            self.pageinfo_cpage.set(0)

    def update_page(self):
        try:
            cpage = self.pageinfo_cpage.get()
        except TclError:
            return
        LABEL_NCH = 40
        LABEL_NCH_PX_FACTOR = 8
        plugins_display = self.cur_plugins_paged[cpage - 1] if self.cur_plugins_paged else []
        self.win[1] /= (
            (
                W(tk.LabelFrame, text=self._getpluginextendedname(pl), fg="green" if pl["is_official"] else "black", font=font10) * Gridder(column=n & 1, row=n // 2, sticky="w") / (
                    W(tk.Frame) * Packer(anchor="w", expand=True, fill="x", side="left") / (
                        W(tk.Label, text=pl["desc"], font=font10, width=LABEL_NCH, height=4, wraplength=LABEL_NCH * LABEL_NCH_PX_FACTOR, justify="left") * Packer(anchor="w", expand=True, fill="x", padx=3, pady=3, side="top"),
                        W(tk.Frame) * Packer(anchor="w", expand=True, fill="x", padx=3, pady=3, side="top") / (
                            (W(tk.Label, text=tag["label"], bg=tag["color"], fg=rrggbb_bg2fg(tag["color"]), font=mono10) * Packer(anchor="w", padx=2, side="left"))
                            for tag in pl["tags"]
                        )
                    ),
                    W(tk.Frame) * Packer(anchor="w", side="left") / (
                        W(tk.Button, text="主页", font=font10, command=partial(system_open, pl["homepage"])) * Packer(anchor="w", expand=True, fill="x", side="top"),
                        W(tk.Button, textvariable=self.pluginvars_e[n], command=partial(self.perform_enable, n), font=font10) * Packer(anchor="w", expand=True, fill="x", side="top"),
                        W(tk.Button, textvariable=self.pluginvars_i[n], command=partial(self.perform_install, n), font=font10) * Packer(anchor="w", expand=True, fill="x", side="top"),
                    )
                )
            ) for n, pl in enumerate(plugins_display)
        )
        self.updpluginvars()

    def _getpluginextendedname(self, plugin):
        return "{name} by {author}".format(**plugin)
    
    def _lock_search_and_page(self, lock: bool):
        self.win[0][0][0].disabled = self.win[0][0][1].disabled = lock
        for w in self.win[3]:
            w.disabled = lock

    def perform_install(self, n: int):
        try:
            cpage = self.pageinfo_cpage.get()
        except TclError:
            return

        self._lock_search_and_page(True)

        target = self.cur_plugins_paged[cpage - 1][n]

        self.win[1][n][1][2].disabled = True
        p, tmp = (
            molecules.perform_pip_install(
                str(find_python(self.context.cwd_str)),
                target["project_link"],
                index=self.context.tmp_index,
                new_win=True
            ) if self.pluginvars_i[n].get() == "安装" else
            molecules.perform_pip_command(
                str(find_python(self.context.cwd_str)),
                "uninstall", target["project_link"],
                new_win=True
            )
        )

        def _restore():
            if p:
                while p.poll() is None:
                    pass
                os.remove(tmp)
                self.context.upddists()
                self.updpluginvars()
                self._lock_search_and_page(False)

        Thread(target=_restore).start()

    def perform_enable(self, n: int):
        try:
            cpage = self.pageinfo_cpage.get()
        except TclError:
            return
        target = self.cur_plugins_paged[cpage - 1][n]["module_name"]
        conf = get_toml_config(self.context.cwd_str)
        if self.pluginvars_e[n].get() == "禁用":
            conf.remove_plugin(target)
        else:
            conf.add_plugin(target)

        self.updpluginvars()

    def do_search(self, *_):
        sortkey = self.sortvar.get()
        if sortkey not in self.sortmethods:
            return

        kwd = self.searchvar.get().lower()
        if not kwd:
            self.cur_plugins_paged = list_paginate(
                self.sortmethods[sortkey](self.all_plugins), self.PAGESIZE
            )
        else:
            kwds = kwd.split()
            self.cur_plugins_paged = list_paginate(
                self.sortmethods[sortkey](
                    [x for x in self.all_plugins if all(k in self.plugin_context(x) for k in kwds)]
                ), self.PAGESIZE
            )
        self.updpageinfo()
        self.gotopage(0)

    def applysearch(self, *_):
        self.search_timer.cancel()
        self.search_timer = Timer(0.5, self.do_search)
        self.search_timer.start()


class AppHelp(Application):
    # Some text
    DRIVERS_NOTICE = (
        "注意：NoneBot2 项目需要*至少一个*驱动器才能正常工作！\n"
        "提示：[None]\u00a0驱动器事实上相当于一个“空”驱动器，在不需要进行外部交互"
        "（如仅使用下面的\u00a0[Console]\u00a0适配器）时可以提供占位。"
    )
    ADAPTERS_NOTICE = (
        "注意：NoneBot2 项目需要*至少一个*适配器才能正常工作！\n"
        "提示：[OneBot V11] 与 [OneBot V12] 是两套不同的协议，它们互不兼容！\n"
        "提示：如果要与 <go-cqhttp> 配合使用，应选择 [OneBot V11] 适配器。\n"
        "提示：[Console] 适配器很适合做一些简单的测试。"
    )
    PYPI_INDEX_NOTICE = (
        "[自定义下载源]可以选择从不同的镜像站下载需要的程序包，一般可以加快下载速度。\n"
        "注意：[https://pypi.org/simple] 是官方的下载源，更新及时但下载速度慢。\n"
        "注意：无法保证使用时镜像源是否已同步最新的程序包，如果下载失败请更换不同的下载源。"
    )
    BLOCK_NOTICE = (
        "提示：通常情况下未安装的模块对应板块无法控制“[启用]”状态，已启用的模块对应板块无法控制“[安装]/[卸载]”状态。\n"
        "提示：现在可以正常禁用已启用但未安装的模块了。"
    )
    HOMEPAGE_T = (
        "欢迎使用 NoneBot Desktop 应用程序。\n\n"
        "本程序旨在减少使用 NoneBot2 时命令行的使用。\n\n"
        "这里包含了本程序的一些功能用法。\n"
        "进入其它标签页查看更多。\n\n"
        "提示：方括号 [] 包裹的内容与实际界面中的控件/文本相对应；\n"
        "提示：尖括号 <> 包裹的内容表明其为外部应用程序；\n"
        "提示：双左引号 `` 包裹的内容表示一个路径（统一使用 Unix 格式）。"
    )
    CREATE_T = (
        "本页介绍了如何使用本程序创建新项目。\n\n"
        "在主界面点击 [项目]菜单 -> [新建项目] 进入创建项目页面。\n\n"
        "在[项目目录]一栏 通过[浏览]选择一个目录 或 直接将路径粘贴至[输入框] 用于创建项目。\n"
        "注意：项目目录*必须*是一个空目录（可以不存在），且避免使用保留名（如\u00a0nonebot\u00a0等）作为项目目录。\n\n"
        "在[驱动器]一栏选择你需要的驱动器（通常是 [FastAPI]）。\n"
        f"{DRIVERS_NOTICE}\n\n"
        "适配器用于与外界进行特定协议的数据交换。\n"
        "在[适配器]一栏选择你需要的适配器。\n"
        f"{ADAPTERS_NOTICE}\n\n"
        "如果需要使用无法从插件商店获取的插件（如自编插件、从源码下载的插件等），请勾选"
        "[预留配置用于开发插件]选项，然后将这些插件正确放入 `src/plugins` 下。\n\n"
        "[创建虚拟环境]可以有效避免因系统 Python 环境混乱造成的一系列问题，建议开启。\n\n"
        f"{PYPI_INDEX_NOTICE}\n\n"
        "创建完成后会自动进入新创建的项目目录。"
    )
    OPENRUN_T = (
        "本页介绍了如何使用本程序打开并运行已有的项目。\n\n"
        "在主界面点击 [项目]菜单 -> [打开项目] 选择你的项目目录 或 直接将路径粘贴至主界面的[输入框]。\n"
        "如果项目目录正确，主界面的[启动]按钮等功能将全部可用。\n"
        "提示：本程序只支持识别有 `pyproject.toml` 或 `bot.py` 的目录作为项目目录。\n\n"
        "正确打开项目目录后，点击 主界面上的[启动] 或 [项目]菜单 -> [启动项目] 来运行项目。\n"
        "提示：项目会在一个新的命令行窗口中运行，Windows 上仅支持使用 <cmd.exe>，Linux 上会自动从 "
        "<gnome-terminal>, <konsole>, <xfce4-terminal>, <xterm>, <st> 中查找可用的终端模拟器。\n"
        "提示：运行结束后窗口不会直接关闭，因此不必担心无法查看程序输出。"
    )
    EDITENV_T = (
        "本页介绍了如何使用本程序编辑项目的配置文件。\n\n"
        "注意：本页中的配置文件均指项目文件夹中的 DotEnv 文件（所有以 `.env` 开头的配置文件）。\n"
        "注意：部分插件并不使用这些配置文件，实际使用时请先查看相关插件文档。\n\n"
        "在主界面点击 [配置]菜单 -> [配置文件编辑器] 进入配置文件编辑页面。\n\n"
        "在[可用配置文件]一栏的[下拉框]中选择需要编辑的配置文件，选择后将自动打开该文件。\n\n"
        "[配置项]一栏列出了当前选中的配置文件中所有的配置项（注释在读取和保存时会被忽略）。\n"
        "每个配置项等号左侧是该配置项的名称（不区分大小写），等号右侧是该配置项的字面值。\n"
        "如果要添加一个新的配置项，点击下方的[新建配置项]按钮，然后自行填写新配置项的名称和值即可。\n"
        "本程序在保存时会自动移除空的配置项，因此如果要删除某个配置项，只需要将其名称或字面值清空即可。\n"
        "编辑完成后，点击[保存]按钮将新的配置写入文件。\n"
        "注意：只有在点击[保存]按钮时更改才会被写入到文件，直接关闭窗口或切换至其他配置文件均会丢失当前更改，"
        "本程序*不会*试图通过任何提示阻止这种行为。"
    )
    DRVMGR_T = (
        "本页介绍了如何使用本程序管理项目使用的驱动器。\n\n"
        "注意：出于一些原因，本程序目前*没有*实现驱动器的卸载功能。\n\n"
        "在主界面点击 [配置]菜单 -> [管理驱动器] 进入驱动器管理页面。\n\n"
        "该页面上列出了可用的驱动器，驱动器名称位于每个板块的左上角，板块中间的内容是驱动器介绍。\n"
        "板块下方有控制启用的按钮（左）和控制安装的按钮（右）。\n"
        f"{BLOCK_NOTICE}\n\n"
        f"{DRIVERS_NOTICE}\n\n"
        f"{PYPI_INDEX_NOTICE}"
    )
    ADPMGR_T = (
        "本页介绍了如何使用本程序管理项目使用的适配器。\n\n"
        "在主界面点击 [配置]菜单 -> [管理适配器] 进入适配器管理页面。\n\n"
        "该页面上列出了可用的适配器，适配器名称位于每个板块的左上角，板块中间的内容是适配器介绍。\n"
        "板块下方有控制启用的按钮（左）和控制安装的按钮（右）。\n"
        f"{BLOCK_NOTICE}\n\n"
        f"{ADAPTERS_NOTICE}\n\n"
        f"{PYPI_INDEX_NOTICE}"
        ""
    )
    PACKENVMGR_T = (
        "本页介绍了如何使用本程序管理项目使用的包环境（通常是本项目的虚拟环境）\n\n"
        "在主界面点击 [配置]菜单 -> [管理环境] 进入环境管理页面。\n\n"
        "页面左侧列表显示了当前环境安装的所有包，*双击*某个包即可查看这个包的信息或管理这个包。\n"
        "界面下方有[更新]和[卸载]按钮，点击即可进行相应操作。\n\n"
        f"{PYPI_INDEX_NOTICE}"
    )
    BUILTINPLG_T = (
        "本页介绍了如何使用本程序管理项目使用的内置插件。\n\n"
        "在主界面点击 [插件]菜单 -> [管理内置插件] 进入内置插件管理页面。\n\n"
        "页面列出了所有的内置插件，每个内置插件可以分别控制[启用]与[禁用]。"
    )
    PLGSTORE_T = (
        "本页介绍了如何使用本程序的插件商店。\n\n"
        "在主界面点击 [插件]菜单 -> [插件商店] 进入插件商店页面。\n\n"
        "页面上方有[搜索]栏和[排序]选项控制显示的内容。"
        "可以在[搜索框]输入关键词（以空格分割）筛选想要的插件，"
        "也可以指定插件的显示顺序。\n"
        "提示：搜索内容不区分大小写。\n\n"
        "页面中间展示了符合搜索条件的插件，一个插件使用一个板块。\n"
        "板块左上角显示了插件的名称和作者，如果标为绿色则此插件为官方插件。\n"
        "板块内部有插件的简介和标签（如果有）。\n"
        "板块右侧有[主页]、[启用/禁用]和[安装/卸载]三个按钮。主页按钮用于前往项目主页，其余略（\n"
        f"{BLOCK_NOTICE}\n\n"
        "页面下方提供了几个翻页跳页的功能。\n\n"
        f"{PYPI_INDEX_NOTICE}"
    )

    def setup(self):
        self.win.title = "NoneBot Desktop - 使用手册"
        name_content = (
            ("主页", self.HOMEPAGE_T),
            ("新建项目", self.CREATE_T),
            ("打开与启动项目", self.OPENRUN_T),
            ("编辑配置文件", self.EDITENV_T),
            ("管理驱动器", self.DRVMGR_T),
            ("管理适配器", self.ADPMGR_T),
            ("管理环境", self.PACKENVMGR_T),
            ("管理内置插件", self.BUILTINPLG_T),
            ("插件商店", self.PLGSTORE_T),
        )

        self.win /= (
            W(ttk.Notebook) * Packer(anchor="nw", expand=True, fill="both") / (
                (
                    W(tk.Label, text=content, justify="left", font=font10, wraplength=620)
                    * NotebookAdder(text=name, padding=2, sticky="nw")
                ) for name, content in name_content
            ),
        )


class AppAbout(Application):
    url = "https://github.com/nonedesktop/nonebot-desktop-tk"
    text = (
        "NoneBot Desktop (Tkinter) 1.0.0\n"
        "(C) 2023 NoneDesktop\n"
        "开发人员：NCBM (Nhanchou Baimin, 南舟白明, worldmozara)\n"
        "该项目使用 MIT 协议开源。\n"
        f"项目主页: {url}"
    )

    def setup(self) -> None:
        self.win.title = "NoneBot Desktop - 关于"
        self.win /= (
            W(tk.Label, text=self.text, font=font10, justify="left", wraplength=480) * Packer(padx=10, pady=10),
            W(tk.Button, text="前往项目主页", font=font10, command=lambda: system_open(self.url)) * Packer(fill="x", expand=True)
        )


t3 = time.perf_counter()
print(f"[GUI] Init Sub Functions: {t3 - t2:.3f}s")


t4 = time.perf_counter()
print(f"[GUI] Main UI Ready: {t4 - t3:.3f}s")
print(f"[GUI] Total: {t4 - t1:.3f}s")


def start_window():
    MainApp(tk.Tk()).run()