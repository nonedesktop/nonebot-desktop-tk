import time

t0 = time.perf_counter()

from functools import partial
from glob import glob
import os
from pathlib import Path
from subprocess import Popen
import sys
from threading import Thread
from typing import Any, Dict, List, Literal, Optional

t1 = time.perf_counter()

import tkinter as tk
from tkinter import BooleanVar, Event, TclError, filedialog, messagebox, StringVar
from tkinter import ttk

t1_1 = time.perf_counter()

from nonebot_desktop import res, exops

t1_2 = time.perf_counter()

from tkreform import Packer, Window
from tkreform.declarative import M, W, Gridder, MenuBinder
from tkreform.menu import MenuCascade, MenuCommand, MenuSeparator
from tkreform.events import LMB, X2
from dotenv.main import DotEnv

t2 = time.perf_counter()

font10 = ("Microsoft Yahei UI", 10)
mono10 = ("Consolas", 10)

win = Window(tk.Tk())

win.title = "NoneBot Desktop"
win.size = 452, 80
win.resizable = False

cwd = StringVar(value="[点击“项目”菜单新建或打开项目]")
tmpindex = StringVar()
curproc: Optional[Popen[bytes]] = None


def cwd_updator(varname: str = "", _unknown: str = "", op: str = ""):
    fp = Path(cwd.get())
    win[1][1].disabled = not fp.is_dir() or not ((fp / "pyproject.toml").is_file() or (fp / "bot.py").is_file())
    m: tk.Menu = win[0].base  # type: ignore
    w = list(m.children.values())[0]
    for entry in (2, 3, 4):
        m.entryconfig(entry, state="disabled" if win[1][1].disabled else "normal")


cwd.trace_add("write", cwd_updator)


def getdist():
    return exops.distributions(*(str(Path(cwd.get()) / si) for si in glob(".venv/**/site-packages", root_dir=cwd.get(), recursive=True)))


def check_pyproject_toml(workdir: Path, master):
    if (workdir / "bot.py").exists():
        if (workdir / "pyproject.toml").exists():
            messagebox.showwarning("警告", "检测到目录下存在 bot.py，其可能不会使用 pyproject.toml 中的配置项。", master=master)
        else:
            messagebox.showerror("错误", "当前目录下没有 pyproject.toml，无法修改配置。", master=master)
            raise Exception("当前目录下没有 pyproject.toml，无法修改配置。")


def create_project():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 新建项目"

    mkwd = StringVar(value="")
    drivervars = [BooleanVar(value=d.name == "FastAPI") for d in res.Data().drivers]
    adaptervars = [BooleanVar(value=False) for _ in res.Data().adapters]
    devplugvar, venvvar = BooleanVar(value=False), BooleanVar(value=True)

    def mkwd_updator(varname: str = "", _unknown: str = "", op: str = ""):
        targetpath = Path(mkwd.get())
        # For valid target:
        # - target is a path
        # - target does not exist or is empty dir
        if not mkwd.get():  # empty path
            subw[0][6].disabled = True
            messagebox.showerror("错误", "路径不能为空", master=subw.base)
        elif targetpath.is_dir() and tuple(targetpath.iterdir()):  # non-empty dir
            subw[0][6].disabled = True
            messagebox.showerror("错误", "目标目录不能非空", master=subw.base)
        elif targetpath.is_file():  # not dir
            subw[0][6].disabled = True
            messagebox.showerror("错误", "目标不能为文件", master=subw.base)
        else:
            subw[0][6].disabled = False

    mkwd.trace_add("write", mkwd_updator)

    subw /= (
        W(tk.Frame) * Gridder() / (
            W(tk.Frame) * Gridder(column=0, row=0) / (
                W(tk.Label, text="项目目录：", font=font10) * Packer(side="left"),
                W(tk.Entry, textvariable=mkwd, font=font10) * Packer(side="left", expand=True),
                W(tk.Button, text="浏览……", font=font10) * Packer(side="left")
            ),
            W(tk.LabelFrame, text="驱动器", font=font10) * Gridder(column=0, sticky="w") / (
                W(tk.Checkbutton, text=f"{dr.name} ({dr.desc})", variable=dv, font=font10) * Packer(side="top", anchor="w")
                for dr, dv in zip(res.Data().drivers, drivervars)
            ),
            W(tk.LabelFrame, text="适配器", font=font10) * Gridder(column=0, sticky="w") / (
                W(tk.Checkbutton, text=f"{ad.name} ({ad.desc})", variable=av, font=font10) * Packer(side="top", anchor="w")
                for ad, av in zip(res.Data().adapters, adaptervars)
            ),
            W(tk.Checkbutton, text="预留配置用于开发插件（将会创建 src/plugins）", variable=devplugvar, font=font10) * Gridder(column=0, sticky="w"),
            W(tk.Checkbutton, text="创建虚拟环境（位于 .venv，用于隔离环境）", variable=venvvar, font=font10) * Gridder(column=0, sticky="w"),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Gridder(column=0, sticky="w") / (
                W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10, width=50) * Packer(side="left", fill="x", expand=True),
            ),
            W(tk.Button, text="创建", font=font10) * Gridder(column=0, sticky="e")
        ),
    )

    @subw[0][0][2].callback
    def finddir():
        mkwd.set(filedialog.askdirectory(parent=subw.base, title="选择项目目录"))

    # subw[0][1][1].base.select()  # type: ignore
    # subw[0][4].base.select()  # type: ignore
    subw[0][6].disabled = True

    def create():
        # print([x.get() for x in drivervars])
        # print([x.get() for x in adaptervars])
        # print(devplugvar.get(), venvvar.get())
        subw[0][6].text = "正在创建项目……"
        subw[0][6].disabled = True
        exops.create(
            mkwd.get(), [d for d, b in zip(res.Data().drivers, drivervars) if b.get()],
            [a for a, b in zip(res.Data().adapters, adaptervars) if b.get()],
            devplugvar.get(), venvvar.get(), tmpindex.get()
        )
        cwd.set(mkwd.get())
        try:
            subw.destroy()
        except TclError:
            pass
        messagebox.showinfo(title="项目创建完成", message="项目创建成功，已自动进入该项目。", master=win.base)

    cth = Thread(target=create)
    subw[0][6].callback(cth.start)


def drvmgr():
    driverenvs: List[StringVar] = [StringVar(value="启用") for _ in res.Data().drivers]  # drivers' states (enabled, disabled)
    drivervars: List[StringVar] = [StringVar(value="安装") for _ in res.Data().drivers]  # drivers' states (installed, not installed)

    def update_drivers():
        distnames = [d.metadata["name"].lower() for d in getdist()]
        _enabled = exops.recursive_find_env_config(cwd.get(), "DRIVER")
        if _enabled is None:
            enabled = []
        else:
            enabled = _enabled.split("+")

        for n, d in enumerate(res.Data().drivers):
            if d.name.lower() in distnames:
                drivervars[n].set("已安装")
            elif d.name != "None":
                drivervars[n].set("安装")
            else:
                drivervars[n].set("内置")
            
            driverenvs[n].set("禁用" if d.module_name in enabled else "启用")

    update_drivers()

    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 管理驱动器"
    subw.resizable = False

    def getnenabledstate(n: int):
        return "disabled" if drivervars[n].get() == "安装" else "normal"

    def getninstalledstate(n: int):
        return "disabled" if drivervars[n].get() == "内置" or drivervars[n].get() == "已安装" else "normal"

    def perform(n: int, op: Literal["enabled", "installed"]):
        target = res.Data().drivers[n]
        if op == "enabled":
            _enabled = exops.recursive_find_env_config(cwd.get(), "DRIVER")
            if _enabled is None:
                enabled = []
            else:
                enabled = _enabled.split("+")

            if target.module_name in enabled:
                enabled.remove(target.module_name)
            else:
                enabled.append(target.module_name)

            exops.recursive_update_env_config(cwd.get(), "DRIVER", "+".join(enabled))

            update_drivers()
            subw[0][n][1][0].base["state"] = getnenabledstate(n)
            subw[0][n][1][1].base["state"] = getninstalledstate(n)
        else:
            cfp = Path(cwd.get())
            subw[0][n][1][1].disabled = True

            p, tmp = exops.exec_new_win(
                cfp,
                f'''"{exops.find_python(cfp)}" -m pip install "{target.project_link}"'''
            )

            def _restore():
                if p:
                    while p.poll() is None:
                        pass
                    os.remove(tmp)
                    update_drivers()
                    subw[0][n][1][0].base["state"] = getnenabledstate(n)
                    subw[0][n][1][1].base["state"] = getninstalledstate(n)

            Thread(target=_restore).start()

    subw /= (
        W(tk.Frame) * Packer(side="top") / (
            (
                W(tk.LabelFrame, text=drv.name, font=font10) * Gridder(column=n & 1, row=n // 2, sticky="nw") / (
                    W(tk.Label, text=drv.desc, font=font10, width=20, height=3, justify="left") * Packer(anchor="nw", side="top"),
                    W(tk.Frame) * Packer(anchor="nw", fill="x", side="top", expand=True) / (
                        W(tk.Button, font=font10, textvariable=driverenvs[n], command=partial(perform, n, "enabled"), state=getnenabledstate(n)) * Packer(fill="x", side="left", expand=True),
                        W(tk.Button, font=font10, textvariable=drivervars[n], command=partial(perform, n, "installed"), state=getninstalledstate(n)) * Packer(fill="x", side="left", expand=True)
                    )
                )
            ) for n, drv in enumerate(res.Data().drivers)
        ),
        W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="top", expand=True) / (
            W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
        )
    )


def adpmgr():
    check_pyproject_toml(Path(cwd.get()), master=win)

    adapterenvs: List[StringVar] = [StringVar(value="启用") for _ in res.Data().adapters]  # drivers' states (enabled, disabled)
    adaptervars: List[StringVar] = [StringVar(value="安装") for _ in res.Data().adapters]  # drivers' states (installed, not installed)

    def update_adapters():
        distnames = [d.metadata["name"].lower() for d in getdist()]

        conf = exops.get_toml_config(cwd.get())
        if not (data := conf._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        _enabled: List[Dict[str, str]] = table.setdefault("adapters", [])
        enabled = [a["module_name"] for a in _enabled]

        for n, d in enumerate(res.Data().adapters):
            adaptervars[n].set("卸载" if d.project_link in distnames else "安装")
            adapterenvs[n].set("禁用" if d.module_name in enabled else "启用")

    update_adapters()

    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 管理适配器"
    subw.resizable = False

    def getnenabledstate(n: int):
        return "disabled" if adaptervars[n].get() == "安装" else "normal"

    def getninstalledstate(n: int):
        return "disabled" if adapterenvs[n].get() == "禁用" else "normal"

    def perform(n: int, op: Literal["enabled", "installed"]):
        target = res.Data().adapters[n]
        if op == "enabled":
            slimtarget = res.NBCLI().config.SimpleInfo.parse_obj(target)
            conf = exops.get_toml_config(cwd.get())
            if adapterenvs[n].get() == "禁用":
                conf.remove_adapter(slimtarget)
            else:
                conf.add_adapter(slimtarget)

            update_adapters()
            subw[0][n][1][0].base["state"] = getnenabledstate(n)
            subw[0][n][1][1].base["state"] = getninstalledstate(n)
        else:
            cfp = Path(cwd.get())
            subw[0][n][1][1].disabled = True
            pip_op = "install" if adaptervars[n].get() == "安装" else "uninstall"

            p, tmp = exops.exec_new_win(
                cfp,
                f'''"{exops.find_python(cfp)}" -m pip {pip_op} "{target.project_link}"'''
            )

            def _restore():
                if p:
                    while p.poll() is None:
                        pass
                    os.remove(tmp)
                    update_adapters()
                    subw[0][n][1][0].base["state"] = getnenabledstate(n)
                    subw[0][n][1][1].base["state"] = getninstalledstate(n)

            Thread(target=_restore).start()

    subw /= (
        W(tk.Frame) * Packer(side="top") / (
            (
                W(tk.LabelFrame, text=adp.name, font=font10) * Gridder(column=n % 3, row=n // 3, sticky="nw") / (
                    W(tk.Label, text=adp.desc, font=font10, width=40, height=3, justify="left") * Packer(anchor="nw", side="top"),
                    W(tk.Frame) * Packer(anchor="nw", fill="x", side="top", expand=True) / (
                        W(tk.Button, font=font10, textvariable=adapterenvs[n], command=partial(perform, n, "enabled"), state=getnenabledstate(n)) * Packer(fill="x", side="left", expand=True),
                        W(tk.Button, font=font10, textvariable=adaptervars[n], command=partial(perform, n, "installed"), state=getninstalledstate(n)) * Packer(fill="x", side="left", expand=True)
                    )
                )
            ) for n, adp in enumerate(res.Data().adapters)
        ),
        W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="top", expand=True) / (
            W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
        )
    )


def builtin_plugins():
    check_pyproject_toml(Path(cwd.get()), win.base)
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 管理内置插件"

    bplugins = res.get_builtin_plugins(str(exops.find_python(Path(cwd.get()))))
    opstate = [StringVar(value="启用") for _ in bplugins]

    def updstate():
        cfg = exops.get_toml_config(cwd.get())
        if not (data := cfg._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        plugins: List[str] = table.setdefault("builtin_plugins", [])
        for n, pl in enumerate(bplugins):
            if pl in plugins:
                opstate[n].set("禁用")
            else:
                opstate[n].set("启用")

    updstate()

    def setnstate(n: int):
        cfg = exops.get_toml_config(cwd.get())
        if opstate[n].get() == "启用":
            cfg.add_builtin_plugin(bplugins[n])
        else:
            cfg.remove_builtin_plugin(bplugins[n])
        updstate()

    subw /= (
        (
            W(tk.Frame) * Packer(anchor="nw", fill="x", side="top") / (
                W(tk.Label, text=bp, font=font10, justify="left") * Packer(anchor="w", expand=True, fill="x", side="left"),
                W(tk.Button, textvariable=opstate[n], command=partial(setnstate, n), font=font10) * Packer(anchor="w", side="left")
            )
        ) for n, bp in enumerate(bplugins)
    )


def enviroman():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 管理环境"
    subw.size = 720, 460

    curdist = ""
    _dist_index = {}
    dists = StringVar()

    def update_dists_list():
        _dists = list(getdist())
        if not _dists:
            _dists = list(exops.current_distros())

        _dist_index.clear()
        _dist_index.update({d.name: d for d in _dists})

        dists.set([x for x in _dist_index])  # type: ignore

    update_dists_list()

    def pkgop(op: str):
        cfp = Path(cwd.get())
        subw[0][0][0].disabled = True
        subw[0][1][2][0].disabled = True
        subw[0][1][1][0].disabled = True
        subw[0][1][1][1].disabled = True
        p, tmp = exops.exec_new_win(
            cfp,
            f'''"{exops.find_python(cfp)}" -m pip {op} "{curdist}"'''
        )

        def _restore():
            if p:
                while p.poll() is None:
                    pass
                os.remove(tmp)
                update_dists_list()
                subw[0][0][0].disabled = False
                subw[0][1][2][0].disabled = False
                _infoupd()

        Thread(target=_restore).start()

    subw /= (
        W(tk.PanedWindow, showhandle=True) * Packer(fill="both", expand=True) / (
            W(tk.LabelFrame, text="程序包", font=font10) / (
                W(tk.Listbox, listvariable=dists, font=mono10) * Packer(side="left", fill="both", expand=True),
                W(ttk.Scrollbar) * Packer(side="right", fill="y")
            ),
            W(tk.LabelFrame, text="详细信息", font=font10) / (
                W(tk.Message, text="双击程序包以查看信息", font=font10, justify="left", width=400) * Packer(anchor="nw", expand=True),
                W(tk.Frame) * Packer(side="bottom", fill="x") / (
                    W(tk.Button, text="更新", command=lambda: pkgop("install -U" + (f" -i {tmpindex.get()}" if tmpindex.get() else "")), font=font10, state="disabled") * Packer(side="left", fill="x", expand=True),
                    W(tk.Button, text="卸载", command=lambda: pkgop("uninstall"), font=font10, state="disabled") * Packer(side="right", fill="x", expand=True)
                ),
                W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", side="bottom", expand=True) / (
                    W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
                )
            )
        ),
    )

    li: tk.Listbox = subw[0][0][0].base  # type: ignore
    sl: ttk.Scrollbar = subw[0][0][1].base  # type: ignore
    li.config(yscrollcommand=sl.set)
    sl.config(command=li.yview)

    def _infoupd():
        if m := _dist_index.get(curdist, None):
            dm = m.metadata
            subw[0][1][0].text = (
                f"名称：{dm['name']}\n"
                f"版本：{dm['version']}\n"
                f"摘要：{dm['summary']}\n"
            )
        else:
            subw[0][1][0].text = "双击程序包以查看信息"

        subw[0][1][1][0].disabled = not m
        subw[0][1][1][1].disabled = not m

    @subw[0][0][0].on(str(LMB - X2))
    def showinfo(event: Event):
        nonlocal curdist
        curdist = event.widget.get(event.widget.curselection())
        _infoupd()


def open_project():
    cwd.set(filedialog.askdirectory(mustexist=True, parent=win.base, title="选择项目目录"))


def start():
    if win[1][1].disabled:
        messagebox.showerror("错误", "当前目录不是正确的项目目录。", master=win.base)
        return
    global curproc
    pdir = Path(cwd.get())
    win[1][0][1].disabled = True
    win[1][1].disabled = True
    curproc, tmp = exops.exec_new_win(pdir, f'''"{sys.executable}" -m nb_cli run''')

    def _restore():
        if curproc:
            while curproc.poll() is None:
                pass
            win[1][0][1].disabled = False
            win[1][1].disabled = False
            os.remove(tmp)

    Thread(target=_restore).start()


def open_pdir():
    if win[1][1].disabled:
        messagebox.showerror("错误", "当前目录不是正确的项目目录。", master=win.base)
        return
    exops.system_open(cwd.get())


def internal_env_edit():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 配置文件编辑器"

    allenvs = exops.find_env_file(cwd.get())
    envf = StringVar(value="[请选择一个配置文件进行编辑]")
    curenv = DotEnv(envf.get())
    curopts = []

    def envf_updator(varname: str = "", _unknown: str = "", op: str = ""):
        invalid = envf.get() not in allenvs
        subw[2][0].disabled = invalid
        subw[2][1].disabled = invalid
        if not invalid:
            nonlocal curenv, curopts
            curenv = DotEnv(Path(cwd.get()) / envf.get())
            curopts = [(StringVar(value=k), StringVar(value=v)) for k, v in curenv.dict().items() if v is not None]
            subw[1] /= (
                W(tk.Frame) * Gridder(column=0, sticky="w") / (
                    W(tk.Entry, textvariable=k, font=mono10) * Packer(side="left"),
                    W(tk.Label, text=" = ", font=mono10) * Packer(side="left"),
                    W(tk.Entry, textvariable=v, font=mono10, width=40) * Packer(side="left")
                ) for k, v in curopts
            )

    envf.trace_add("write", envf_updator)

    def new_opt():
        k, v = StringVar(value="参数名"), StringVar(value="值")
        curopts.append((k, v))
        _row = subw[1].add_widget(tk.Frame)
        _row.grid(column=0, sticky="w")
        _key = _row.add_widget(tk.Entry, textvariable=k, font=mono10)
        _lbl = _row.add_widget(tk.Label, text=" = ", font=mono10)
        _val = _row.add_widget(tk.Entry, textvariable=v, font=mono10, width=40)
        _key.pack(side="left")
        _lbl.pack(side="left")
        _val.pack(side="left")

    def save_env():
        with open(Path(cwd.get()) / envf.get(), "w") as f:
            f.writelines(f"{k}={v}\n" for k, v in ((_k.get(), _v.get()) for _k, _v in curopts) if k and v)

        def _success():
            subw[2][1].text = "已保存"
            time.sleep(3)
            subw[2][1].text = "保存"

        envf_updator()

        Thread(target=_success).start()

    subw /= (
        W(tk.LabelFrame, text="可用配置文件", font=font10) * Gridder(column=0, sticky="w") / (
            W(ttk.Combobox, font=font10, textvariable=envf, value=allenvs, width=50) * Packer(expand=True),
        ),
        W(tk.LabelFrame, text="配置项", font=font10) * Gridder(column=0, sticky="w"),
        W(tk.Frame) * Gridder(column=0, sticky="e") / (
            W(tk.Button, text="新建配置项", font=font10, command=new_opt) * Packer(side="left"),
            W(tk.Button, text="保存", font=font10, command=save_env) * Packer(side="right"),
        )
    )
    envf_updator()


def plugin_store():
    check_pyproject_toml(Path(cwd.get()), win.base)
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 插件商店"

    all_plugins_paged = res.list_paginate(res.Data().raw_plugins, 10)
    cur_plugins_paged = all_plugins_paged
    pageinfo_cpage = 0
    pageinfo_mpage = len(all_plugins_paged)

    def _getrealpageinfo():
        return f"第 {pageinfo_cpage + 1}/{pageinfo_mpage} 页"

    def _getpluginextendedname(plugin):
        if plugin["name"] == plugin["project_link"]:
            return "{name} by {author}".format(**plugin)
        if plugin["project_link"].startswith("git+"):
            return "{name} (git+...) by {author}".format(**plugin)
        return "{name} ({project_link}) by {author}".format(**plugin)

    subw /= (
        W(tk.LabelFrame, text="搜索", font=font10) * Packer(anchor="nw", expand=True, fill="x") / (
            W(tk.Entry, font=font10) * Packer(expand=True, fill="x"),
        ),
        W(tk.LabelFrame, text=_getrealpageinfo(), font=font10) * Packer(anchor="w", expand=True, fill="x"),
        W(tk.Frame) * Packer(anchor="sw", expand=True, fill="x") / (
            W(tk.Button, text="首页", font=font10, command=lambda: chpage(-pageinfo_cpage)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(tk.Button, text="上一页", font=font10, command=lambda: chpage(-1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(ttk.Combobox, font=font10) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(tk.Button, text="下一页", font=font10, command=lambda: chpage(1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(tk.Button, text="尾页", font=font10, command=lambda: chpage(pageinfo_mpage - pageinfo_cpage - 1)) * Packer(anchor="nw", expand=True, fill="x", side="left")
        )
    )

    def update_page():
        plugins_display = [x for x in all_plugins_paged[pageinfo_cpage]]
        subw[1] /= (
            (
                W(tk.LabelFrame, text=_getpluginextendedname(pl), font=font10) * Gridder(column=n & 1, row=n // 2, sticky="w") / (
                    W(tk.Label, text=pl["desc"], font=font10, width=40, height=4, wraplength=320, justify="left") * Packer(anchor="w", expand=True, fill="x", padx=5, pady=5, side="left"),
                    W(tk.Button, text="主页", font=font10) * Packer(anchor="w", side="left"),
                    W(tk.Button, text="enable", font=font10) * Packer(anchor="w", side="left"),
                    W(tk.Button, text="install", font=font10) * Packer(anchor="w", side="left"),
                )
            ) for n, pl in enumerate(plugins_display)
        )

    def chpage(offset: int):
        nonlocal pageinfo_cpage
        pageinfo_cpage = (pageinfo_cpage + offset) % pageinfo_mpage
        subw[1].text = _getrealpageinfo()
        update_page()

    update_page()


def app_help():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 使用手册"

    # W.I.P.
    subw /= ()


def app_about():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 关于"

    url = "https://github.com/NCBM/nonebot-desktop-tk"
    msg = subw.add_widget(tk.Message, width=400, font=font10)
    msg.text = (
        "NoneBot Desktop (Tkinter) 1.0.0a1\n"
        "(C) 2023 NCBM (Nhanchou Baimin, 南舟白明, worldmozara)\n"
        "该项目使用 MIT 协议开源。\n"
        f"项目主页: {url}"
    )
    msg.pack(padx=10, pady=10)

    hpg = subw.add_widget(tk.Button, font=font10)
    hpg.text = "前往项目主页"
    hpg.command(lambda: exops.system_open(url))
    hpg.pack(fill="x", expand=True)


t3 = time.perf_counter()

win /= (
    W(tk.Menu) * MenuBinder(win) / (
        M(MenuCascade(label="项目", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="新建项目", font=font10, command=create_project),
            MenuCommand(label="打开项目", font=font10, command=open_project),
            MenuCommand(label="启动项目", font=font10, command=start),
            MenuSeparator(),
            MenuCommand(label="打开项目文件夹", font=font10, command=open_pdir),
            MenuSeparator(),
            MenuCommand(label="退出", font=font10, command=win.destroy, accelerator="Alt+F4")
        ),
        M(MenuCascade(label="配置", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="配置文件编辑器", command=internal_env_edit, font=font10),
            MenuSeparator(),
            MenuCommand(label="管理驱动器", command=drvmgr, font=font10),
            MenuCommand(label="管理适配器", command=adpmgr, font=font10),
            MenuSeparator(),
            MenuCommand(label="管理环境", command=enviroman, font=font10)
        ),
        M(MenuCascade(label="插件", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="管理内置插件", command=builtin_plugins, font=font10),
            MenuCommand(label="插件商店", command=plugin_store, font=font10),
        ),
        M(MenuCascade(label="高级", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="打开命令行窗口", font=font10, command=lambda: exops.open_new_win(Path(cwd.get()))),
            MenuSeparator(),
            MenuCommand(label="编辑 pyproject.toml", font=font10, command=lambda: exops.system_open(Path(cwd.get()) / "pyproject.toml"))
        ),
        M(MenuCascade(label="帮助", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="使用手册", command=app_help, font=font10),
            MenuCommand(label="关于", command=app_about, font=font10)
        )
    ),
    W(tk.Frame) * Gridder() / (
        W(tk.Frame) * Gridder() / (
            W(tk.Label, text="当前路径：", font=("Microsoft Yahei UI", 12)) * Packer(side="left"),
            W(tk.Entry, textvariable=cwd, font=("Microsoft Yahei UI", 12), width=40) * Packer(side="left", expand=True)
        ),
        W(tk.Button, text="启动", command=start, font=("Microsoft Yahei UI", 20)) * Gridder(row=1, sticky="w")
    )
)

cwd_updator()

t4 = time.perf_counter()


def start_window():
    print(f"Import base: {t1 - t0:.3f}s")
    print(f"Import tkinter: {t1_1 - t1:.3f}s")
    print(f"Import this module: {t1_2 - t1_1:.3f}s")
    print(f"Import rest modules: {t2 - t1_2:.3f}s")
    print(f"Init Sub Functions: {t3 - t2:.3f}s")
    print(f"Main UI Ready: {t4 - t3:.3f}s")
    print(f"Total: {t4 - t1:.3f}s")
    Thread(target=res.Data).start()
    win.loop()