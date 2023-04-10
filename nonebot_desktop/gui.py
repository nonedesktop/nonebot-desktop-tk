import time

t0 = time.perf_counter()

from functools import partial
from glob import glob
import os
from pathlib import Path
from subprocess import Popen
import sys
from threading import Thread, Timer
from typing import Any, Dict, List, Literal, Optional

t1 = time.perf_counter()
print(f"[GUI] Import base: {t1 - t0:.3f}s")

import tkinter as tk
from tkinter import BooleanVar, Event, IntVar, TclError, filedialog, messagebox, StringVar
from tkinter import ttk

t1_1 = time.perf_counter()
print(f"[GUI] Import tkinter: {t1_1 - t1:.3f}s")

from nonebot_desktop import res, exops

t1_2 = time.perf_counter()
print(f"[GUI] Import this module: {t1_2 - t1_1:.3f}s")

from tkreform import Packer, Window
from tkreform.base import Application
from tkreform.declarative import M, W, Gridder, MenuBinder
from tkreform.menu import MenuCascade, MenuCommand, MenuSeparator
from tkreform.events import LMB, X2
from dotenv.main import DotEnv

t2 = time.perf_counter()
print(f"[GUI] Import rest modules: {t2 - t1_2:.3f}s")

Thread(target=res.Data, daemon=True).start()

font10 = ("Microsoft Yahei UI", 10)
mono10 = ("Consolas", 10)

win = Window(tk.Tk())

win.title = "NoneBot Desktop"
win.size = 452, 80
win.resizable = False

cwd = StringVar(value="[点击“项目”菜单新建或打开项目]")
tmpindex = StringVar()
curproc: Optional[Popen[bytes]] = None
curdistnames: List[str] = []


def upddists():
    global curdistnames
    curdistnames = [d.metadata["name"].lower() for d in getdist()]
    print("[upddists] Updated current dists")


def cwd_updator(varname: str = "", _unknown: str = "", op: str = ""):
    fp = Path(cwd.get())
    win[1][1].disabled = not fp.is_dir() or not ((fp / "pyproject.toml").is_file() or (fp / "bot.py").is_file())
    m: tk.Menu = win[0].base  # type: ignore
    w = list(m.children.values())[0]
    for entry in (2, 3, 4):
        m.entryconfig(entry, state="disabled" if win[1][1].disabled else "normal")
    if win[1][1].disabled:
        return
    Thread(target=upddists).start()
    print(f"[cwd_updator] Current directory is set to {cwd.get()!r}")


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


def bg2fg(color: str):
    c_int = int(color[1:], base=16)
    # c_rsh = (len(color) - 1) // 3
    # c_msk = 0xf  # 0b00001111
    # for _ in range(1, c_rsh):
    #     c_msk = (c_msk << 4) + c_msk
    #
    # Formula for choosing color:
    # 0.2126 × R + 0.7152 × G + 0.0722 × B > 0.5
    c_bgr: List[int] = []
    for _ in range(3):
        c_bgr.append(c_int & 0xff)
        c_int >>= 8
    b, g, r = (x / 255 for x in c_bgr)
    return "#{0:02x}{0:02x}{0:02x}".format(0xff * int(0.2126 * r + 0.7152 * g + 0.0722 * b < 0.5))


class CreateProject(Application):
    def setup(self) -> None:
        self.win.title = "NoneBot Desktop - 新建项目"
        self.win.base.grab_set()
        self.create_target = StringVar()
        self.driver_select_state = [BooleanVar(value=d.name == "FastAPI") for d in res.Data().drivers]
        self.adapter_select_state = [BooleanVar(value=False) for _ in res.Data().adapters]
        self.dev_mode = BooleanVar(value=False)
        self.use_venv = BooleanVar(value=True)

        self.win /= (
            W(tk.Frame) * Packer(fill="x", expand=True) / (
                W(tk.Label, text="项目目录：", font=font10) * Packer(side="left"),
                W(tk.Entry, textvariable=self.create_target, font=font10) * Packer(side="left", expand=True),
                W(tk.Button, text="浏览……", font=font10, command=self.ct_browse) * Packer(side="left")
            ),
            W(tk.LabelFrame, text="驱动器", font=font10) * Packer(fill="x", expand=True) / (
                W(tk.Checkbutton, text=f"{dr.name} ({dr.desc})", variable=dv, font=font10) * Packer(side="top", anchor="w")
                for dr, dv in zip(res.Data().drivers, self.driver_select_state)
            ),
            W(tk.LabelFrame, text="适配器", font=font10) * Packer(fill="x", expand=True) / (
                W(tk.Checkbutton, text=f"{ad.name} ({ad.desc})", variable=av, font=font10) * Packer(side="top", anchor="w")
                for ad, av in zip(res.Data().adapters, self.adapter_select_state)
            ),
            W(tk.Checkbutton, text="预留配置用于开发插件（将会创建 src/plugins）", variable=self.dev_mode, font=font10) * Packer(fill="x", expand=True, anchor="w"),
            W(tk.Checkbutton, text="创建虚拟环境（位于 .venv，用于隔离环境）", variable=self.use_venv, font=font10) * Packer(fill="x", expand=True, anchor="w"),
            W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(fill="x", expand=True) / (
                W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10, width=50) * Packer(side="left", fill="x", expand=True),
            ),
            W(tk.Frame) * Packer(fill="x", expand=True)
        )

        self.create_btn = self.win[6].add_widget(tk.Button, text="创建", font=font10)
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

    def ct_checker(self, *_):
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

    def ct_browse(self):
        self.ct_str = filedialog.askdirectory(parent=self.win.base, title="选择项目目录")

    def perform_create(self):
        drivs = [d for d, b in zip(res.Data().drivers, self.driver_select_state) if b.get()]
        adaps = [a for a, b in zip(res.Data().adapters, self.adapter_select_state) if b.get()]
        if not drivs:
            messagebox.showerror("错误", "NoneBot2 项目需要*至少一个*驱动器才能正常工作！", master=self.win.base)
            return
        if not adaps:
            messagebox.showerror("错误", "NoneBot2 项目需要*至少一个*适配器才能正常工作！", master=self.win.base)
            return
        self.create_btn.text = "正在创建项目……"
        self.create_btn.disabled = True
        exops.create(
            self.ct_str, drivs, adaps, self.dev_mode.get(), self.use_venv.get(), tmpindex.get()
        )
        cwd.set(self.ct_str)
        try:
            self.win.destroy()
        except TclError:
            pass
        messagebox.showinfo(title="项目创建完成", message="项目创建成功，已自动进入该项目。", master=win.base)


def drvmgr():
    driverenvs: List[StringVar] = [StringVar(value="启用") for _ in res.Data().drivers]  # drivers' states (enabled, disabled)
    drivervars: List[StringVar] = [StringVar(value="安装") for _ in res.Data().drivers]  # drivers' states (installed, not installed)

    def update_drivers():
        _enabled = exops.recursive_find_env_config(cwd.get(), "DRIVER")
        if _enabled is None:
            enabled = []
        else:
            enabled = _enabled.split("+")

        for n, d in enumerate(res.Data().drivers):
            if d.name.lower() in curdistnames:
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
    subw.base.grab_set()

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

            upddists()
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

    adapterenvs: List[StringVar] = [StringVar(value="启用") for _ in res.Data().adapters]  # adapters' states (enabled, disabled)
    adaptervars: List[StringVar] = [StringVar(value="安装") for _ in res.Data().adapters]  # adapters' states (installed, not installed)

    def update_adapters():
        conf = exops.get_toml_config(cwd.get())
        if not (data := conf._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        _enabled: List[Dict[str, str]] = table.setdefault("adapters", [])
        enabled = [a["module_name"] for a in _enabled]

        for n, d in enumerate(res.Data().adapters):
            adaptervars[n].set("卸载" if d.project_link in curdistnames else "安装")
            adapterenvs[n].set("禁用" if d.module_name in enabled else "启用")

    update_adapters()

    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 管理适配器"
    subw.resizable = False
    subw.base.grab_set()

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
                    upddists()
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
    subw.base.grab_set()

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
    subw.base.grab_set()

    curdist = ""
    _dist_index = {}
    dists = StringVar()

    def update_dists_list():
        _dists = list(getdist())
        if not _dists:
            _dists = list(exops.current_distros())

        _dist_index.clear()
        _dist_index.update({d.name: d for d in _dists})

        global curdistnames
        dists.set(curdistnames := [x for x in _dist_index])  # type: ignore
        print("[environman::update_dists_list] Updated current distnames in global")

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
    subw.base.grab_set()

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
    subw.base.grab_set()

    PAGESIZE = 8
    all_plugins = res.Data().raw_plugins
    all_plugins_paged = res.list_paginate(all_plugins, PAGESIZE)
    cur_plugins_paged = all_plugins_paged
    pageinfo_cpage = IntVar(value=1)
    pageinfo_mpage = len(cur_plugins_paged)
    pluginvars_i = [StringVar(value="安装") for _ in range(PAGESIZE)]
    pluginvars_e = [StringVar(value="启用") for _ in range(PAGESIZE)]

    def updpluginvars():
        try:
            cpage = pageinfo_cpage.get()
        except TclError:
            return
        curpage = cur_plugins_paged[cpage - 1] if cur_plugins_paged else []
        conf = exops.get_toml_config(cwd.get())
        if not (data := conf._get_data()):
            raise RuntimeError("Config file not found!")
        table: Dict[str, Any] = data.setdefault("tool", {}).setdefault("nonebot", {})
        _enabled: List[str] = table.setdefault("plugins", [])
        enabled = [a for a in _enabled]

        for n, d in enumerate(curpage):
            pluginvars_i[n].set("卸载" if d["project_link"] in curdistnames else "安装")
            pluginvars_e[n].set("禁用" if d["module_name"] in enabled else "启用")

    def getnenabledstate(n: int):
        return "disabled" if pluginvars_i[n].get() == "安装" else "normal"

    def getninstalledstate(n: int):
        return "disabled" if pluginvars_e[n].get() == "禁用" else "normal"

    @partial(pageinfo_cpage.trace_add, "write")
    def changepageno(*_):
        subw[1].text = _getrealpageinfo()
        update_page()

    def updpageinfo():
        nonlocal pageinfo_mpage
        pageinfo_cpage.set(1)
        pageinfo_mpage = len(cur_plugins_paged)
        subw[3][2].base["values"] = list(range(1, pageinfo_mpage + 1))

    def plugin_context(pl):
        return (
            "{name} {project_link} {module_name} {author} ".format(**pl) +
            " ".join(tag["label"] for tag in pl["tags"])
        ).lower()

    searchvar = StringVar(value="")
    search_timer = Timer(0.8, lambda: None)

    sortvar = StringVar(value="发布时间（旧-新）")
    sortvalues = {
        "发布时间（旧-新）": lambda x: x,
        "发布时间（新-旧）": lambda x: list(reversed(x)),
        "模块名（A-Z）": lambda x: sorted(x, key=lambda p: p["module_name"]),
    }

    def do_search(*_):
        sortkey = sortvar.get()
        if sortkey not in sortvalues:
            return
        nonlocal cur_plugins_paged
        kwd = searchvar.get().lower()
        if not kwd:
            cur_plugins_paged = res.list_paginate(sortvalues[sortkey](all_plugins), PAGESIZE)
        else:
            kwds = kwd.split()
            cur_plugins_paged = res.list_paginate(
                sortvalues[sortkey]([x for x in all_plugins if all(k in plugin_context(x) for k in kwds)]),
                PAGESIZE
            )
        updpageinfo()
        gotopage(0)

    sortvar.trace_add("write", do_search)

    @partial(searchvar.trace_add, "write")
    def applysearch(*_):
        nonlocal search_timer
        search_timer.cancel()
        search_timer = Timer(0.5, do_search)
        search_timer.start()

    def _getrealpageinfo():
        try:
            cpage = pageinfo_cpage.get()
            return f"第 {cpage}/{pageinfo_mpage} 页"
        except TclError:
            return subw[1].text

    def _getpluginextendedname(plugin):
        # if plugin["name"] == plugin["project_link"]:
        #     return "{name} by {author}".format(**plugin)
        # if plugin["project_link"].startswith("git+"):
        #     return "{name} (git+...) by {author}".format(**plugin)
        # return "{name} ({project_link}) by {author}".format(**plugin)
        return "{name} by {author}".format(**plugin)

    def perform_install(n: int):
        try:
            cpage = pageinfo_cpage.get()
        except TclError:
            return

        subw[0][0][0].disabled = True
        for i in range(5):
            subw[3][i].disabled = True

        target = cur_plugins_paged[cpage - 1][n]
        cfp = Path(cwd.get())
        subw[1][n][1][2].disabled = True
        pip_op = "install" if pluginvars_i[n].get() == "安装" else "uninstall"

        p, tmp = exops.exec_new_win(
            cfp,
            f'''"{exops.find_python(cfp)}" -m pip {pip_op} "{target['project_link']}"'''
        )

        def _restore():
            if p:
                while p.poll() is None:
                    pass
                os.remove(tmp)
                upddists()
                updpluginvars()
                subw[1][n][1][1].base["state"] = getnenabledstate(n)
                subw[1][n][1][2].base["state"] = getninstalledstate(n)
                subw[0][0][0].disabled = False
                for i in range(5):
                    subw[3][i].disabled = False

        Thread(target=_restore).start()

    def perform_enable(n: int):
        try:
            cpage = pageinfo_cpage.get()
        except TclError:
            return
        target = cur_plugins_paged[cpage - 1][n]["module_name"]
        conf = exops.get_toml_config(cwd.get())
        if pluginvars_e[n].get() == "禁用":
            conf.remove_plugin(target)
        else:
            conf.add_plugin(target)

        updpluginvars()
        subw[1][n][1][1].base["state"] = getnenabledstate(n)
        subw[1][n][1][2].base["state"] = getninstalledstate(n)

    subw /= (
        W(tk.Frame) * Packer(anchor="nw", expand=True, fill="x") / (
            W(tk.LabelFrame, text="搜索", font=font10) * Packer(anchor="nw", expand=True, fill="x", side="left") / (
                W(tk.Entry, textvariable=searchvar, font=font10) * Packer(expand=True, fill="x"),
            ),
            W(tk.LabelFrame, text="排序", font=font10) * Packer(anchor="nw", side="left") / (
                W(ttk.Combobox, textvariable=sortvar, value=list(sortvalues.keys()), font=font10) * Packer(expand=True, fill="x"),
            ),
        ),
        W(tk.LabelFrame, text=_getrealpageinfo(), font=font10) * Packer(anchor="nw", expand=True, fill="x"),
        W(tk.LabelFrame, text="自定义下载源", font=font10) * Packer(anchor="sw", fill="x", expand=True) / (
            W(ttk.Combobox, textvariable=tmpindex, value=res.PYPI_MIRRORS, font=mono10) * Packer(side="left", fill="x", expand=True),
        ),
        W(tk.Frame) * Packer(anchor="sw", expand=True, fill="x") / (
            W(tk.Button, text="首页", font=font10, command=lambda: gotopage(0)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(tk.Button, text="上一页", font=font10, command=lambda: chpage(-1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(ttk.Combobox, textvariable=pageinfo_cpage, width=8, font=("Microsoft Yahei UI", 14)) * Packer(anchor="nw", side="left"),
            W(tk.Button, text="下一页", font=font10, command=lambda: chpage(1)) * Packer(anchor="nw", expand=True, fill="x", side="left"),
            W(tk.Button, text="尾页", font=font10, command=lambda: gotopage(-1)) * Packer(anchor="nw", expand=True, fill="x", side="left")
        )
    )

    def update_page():
        try:
            cpage = pageinfo_cpage.get()
        except TclError:
            return
        updpluginvars()
        LABEL_NCH = 40
        LABEL_NCH_PX_FACTOR = 8
        plugins_display = cur_plugins_paged[cpage - 1] if cur_plugins_paged else []
        subw[1] /= (
            (
                W(tk.LabelFrame, text=_getpluginextendedname(pl), fg="green" if pl["is_official"] else "black", font=font10) * Gridder(column=n & 1, row=n // 2, sticky="w") / (
                    W(tk.Frame) * Packer(anchor="w", expand=True, fill="x", side="left") / (
                        W(tk.Label, text=pl["desc"], font=font10, width=LABEL_NCH, height=4, wraplength=LABEL_NCH * LABEL_NCH_PX_FACTOR, justify="left") * Packer(anchor="w", expand=True, fill="x", padx=3, pady=3, side="top"),
                        W(tk.Frame) * Packer(anchor="w", expand=True, fill="x", padx=3, pady=3, side="top") / (
                            (W(tk.Label, text=tag["label"], bg=tag["color"], fg=bg2fg(tag["color"]), font=mono10) * Packer(anchor="w", padx=2, side="left"))
                            for tag in pl["tags"]
                        )
                    ),
                    W(tk.Frame) * Packer(anchor="w", side="left") / (
                        W(tk.Button, text="主页", font=font10, command=partial(exops.system_open, pl["homepage"])) * Packer(anchor="w", expand=True, fill="x", side="top"),
                        W(tk.Button, textvariable=pluginvars_e[n], command=partial(perform_enable, n), state=getnenabledstate(n), font=font10) * Packer(anchor="w", expand=True, fill="x", side="top"),
                        W(tk.Button, textvariable=pluginvars_i[n], command=partial(perform_install, n), state=getninstalledstate(n), font=font10) * Packer(anchor="w", expand=True, fill="x", side="top"),
                    )
                )
            ) for n, pl in enumerate(plugins_display)
        )

    def chpage(offset: int):
        if pageinfo_mpage:
            pageinfo_cpage.set((pageinfo_cpage.get() - 1 + offset) % pageinfo_mpage + 1)
        else:
            pageinfo_cpage.set(0)

    def gotopage(page: int):
        if pageinfo_mpage:
            pageinfo_cpage.set(page % pageinfo_mpage + 1)
        else:
            pageinfo_cpage.set(0)

    updpageinfo()
    update_page()


def app_help():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 使用手册"

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

    # W.I.P.
    nb = subw.add_widget(ttk.Notebook)
    pg_home = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_home.text = (
        "欢迎使用 NoneBot Desktop 应用程序。\n\n"
        "本程序旨在减少使用 NoneBot2 时命令行的使用。\n\n"
        "这里包含了本程序的一些功能用法。\n"
        "进入其它标签页查看更多。\n\n"
        "提示：方括号 [] 包裹的内容与实际界面中的控件/文本相对应；\n"
        "提示：尖括号 <> 包裹的内容表明其为外部应用程序；\n"
        "提示：双左引号 `` 包裹的内容表示一个路径（统一使用 Unix 格式）。"
    )
    pg_create = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_create.text = (
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
    pg_openrun = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_openrun.text = (
        "本页介绍了如何使用本程序打开并运行已有的项目。\n\n"
        "在主界面点击 [项目]菜单 -> [打开项目] 选择你的项目目录 或 直接将路径粘贴至主界面的[输入框]。\n"
        "如果项目目录正确，主界面的[启动]按钮等功能将全部可用。\n"
        "提示：本程序只支持识别有 `pyproject.toml` 或 `bot.py` 的目录作为项目目录。\n\n"
        "正确打开项目目录后，点击 主界面上的[启动] 或 [项目]菜单 -> [启动项目] 来运行项目。\n"
        "提示：项目会在一个新的命令行窗口中运行，Windows 上仅支持使用 <cmd.exe>，Linux 上会自动从 "
        "<gnome-terminal>, <konsole>, <xfce4-terminal>, <xterm>, <st> 中查找可用的终端模拟器。\n"
        "提示：运行结束后窗口不会直接关闭，因此不必担心无法查看程序输出。"
    )
    pg_editenv = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_editenv.text = (
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
    pg_drvmgr = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_drvmgr.text = (
        "本页介绍了如何使用本程序管理项目使用的驱动器。\n\n"
        "注意：出于一些原因，本程序目前*没有*实现驱动器的卸载功能。\n\n"
    )
    pg_adpmgr = nb.add_widget(tk.Label, justify="left", font=font10, wraplength=600)
    pg_adpmgr.text = (
        "本页介绍了如何使用本程序管理项目使用的适配器。\n\n"
        ""
    )
    nb.base.add(pg_home.base, text="主页", padding=(2, 2))  # type: ignore
    nb.base.add(pg_create.base, text="新建项目", padding=(2, 2))  # type: ignore
    nb.base.add(pg_openrun.base, text="打开与启动项目", padding=(2, 2))  # type: ignore
    nb.base.add(pg_editenv.base, text="编辑配置文件", padding=(2, 2))  # type: ignore
    nb.base.add(pg_drvmgr.base, text="管理驱动器", padding=(2, 2))  # type: ignore
    nb.base.add(pg_adpmgr.base, text="管理适配器", padding=(2, 2))  # type: ignore
    nb.pack(anchor="nw", expand=True, fill="both")


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
print(f"[GUI] Init Sub Functions: {t3 - t2:.3f}s")

win /= (
    W(tk.Menu) * MenuBinder(win) / (
        M(MenuCascade(label="项目", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="新建项目", font=font10, command=lambda: CreateProject(win.sub_window())),
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
print(f"[GUI] Main UI Ready: {t4 - t3:.3f}s")
print(f"[GUI] Total: {t4 - t1:.3f}s")


def start_window():
    win.loop()