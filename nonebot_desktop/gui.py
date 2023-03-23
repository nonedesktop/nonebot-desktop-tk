from locale import getpreferredencoding
import os
from pathlib import Path
from subprocess import Popen
import sys
from threading import Thread
import tkinter as tk
from tkinter import BooleanVar, filedialog, messagebox, StringVar
from typing import Optional
from nonebot_desktop import res, exops
from tkreform import Packer, Window
from tkreform.declarative import M, W, Gridder, MenuBinder
from tkreform.menu import MenuCascade, MenuCommand, MenuSeparator

font10 = ("Microsoft Yahei UI", 10)

win = Window(tk.Tk())

win.title = "NoneBot Desktop"
win.size = 456, 80
win.resizable = False

cwd = StringVar(value="[点击“项目”菜单新建或打开项目]")
curproc: Optional[Popen[bytes]] = None


def cwd_updator(varname: str, _unknown: str, op: str):
    fp = Path(cwd.get())
    win[1][1].disabled = not fp.is_dir() or not ((fp / "pyproject.toml").is_file() or (fp / "bot.py").is_file())


cwd.trace_add("write", cwd_updator)


def create_project():
    subw = win.sub_window()
    subw.title = "NoneBot Desktop - 新建项目"

    mkwd = StringVar(value="")
    drivervars = [BooleanVar(value=d.name == "FastAPI") for d in res.drivers]
    adaptervars = [BooleanVar(value=False) for _ in res.adapters]
    devplugvar, venvvar = BooleanVar(value=False), BooleanVar(value=True)

    def mkwd_updator(varname: str, _unknown: str, op: str):
        subw[0][5].disabled = not mkwd.get()

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
                for dr, dv in zip(res.drivers, drivervars)
            ),
            W(tk.LabelFrame, text="适配器") * Gridder(column=0, sticky="w") / (
                W(tk.Checkbutton, text=f"{ad.name} ({ad.desc})", variable=av, font=font10) * Packer(side="top", anchor="w")
                for ad, av in zip(res.adapters, adaptervars)
            ),
            W(tk.Checkbutton, text="预留配置用于开发插件（将会创建 src/plugins）", variable=devplugvar, font=font10) * Gridder(column=0, sticky="w"),
            W(tk.Checkbutton, text="创建虚拟环境（位于 .venv，用于隔离环境）", variable=venvvar, font=font10) * Gridder(column=0, sticky="w"),
            W(tk.Button, text="创建", font=font10) * Gridder(column=0, sticky="e")
        ),
    )

    @subw[0][0][2].callback
    def finddir():
        mkwd.set(filedialog.askdirectory(parent=subw.base, title="选择项目目录"))

    # subw[0][1][1].base.select()  # type: ignore
    # subw[0][4].base.select()  # type: ignore
    subw[0][5].disabled = True

    def create():
        # print([x.get() for x in drivervars])
        # print([x.get() for x in adaptervars])
        # print(devplugvar.get(), venvvar.get())
        subw[0][5].text = "正在创建项目……"
        subw[0][5].disabled = True
        exops.create(
            mkwd.get(), [d for d, b in zip(res.drivers, drivervars) if b.get()],
            [a for a, b in zip(res.adapters, adaptervars) if b.get()],
            devplugvar.get(), venvvar.get()
        )
        cwd.set(mkwd.get())
        subw.destroy()
        messagebox.showinfo(title="项目创建完成", message="项目创建成功，已自动进入该项目。", master=win.base)

    cth = Thread(target=create)
    subw[0][5].callback(cth.start)


def open_project():
    cwd.set(filedialog.askdirectory(mustexist=True, parent=win.base, title="选择项目目录"))


def start():
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


win /= (
    W(tk.Menu) * MenuBinder(win) / (
        M(MenuCascade(label="项目", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="新建项目", font=font10, command=create_project, accelerator="Ctrl+N"),
            MenuCommand(label="打开项目", font=font10, command=open_project, accelerator="Ctrl+O"),
            MenuCommand(label="启动项目", font=font10, command=start, accelerator="F5"),
            MenuSeparator(),
            MenuCommand(label="退出", font=font10, command=win.destroy, accelerator="Alt+F4")
        ),
        M(MenuCascade(label="配置", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="内置配置文件编辑器", font=font10),
            MenuCommand(label="使用外部应用程序编辑配置文件", font=font10),
            MenuSeparator(),
            MenuCommand(label="管理驱动器", font=font10),
            MenuSeparator(),
            MenuCommand(label="管理适配器", font=font10),
            MenuSeparator(),
            MenuCommand(label="管理虚拟环境", font=font10)
        ),
        M(MenuCascade(label="插件", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="插件商店", font=font10),
        ),
        M(MenuCascade(label="高级", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="打开命令行窗口", font=font10),
            MenuSeparator(),
            MenuCommand(label="创建插件", font=font10),
            MenuSeparator(),
            MenuCommand(label="释放 bot.py", font=font10),
            MenuCommand(label="编辑 bot.py", font=font10),
            MenuSeparator(),
            MenuCommand(label="编辑 pyproject.toml", font=font10)
        ),
        M(MenuCascade(label="帮助", font=font10), tearoff=False) * MenuBinder() / (
            MenuCommand(label="使用手册", font=font10),
            MenuCommand(label="关于", font=font10)
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

win[1][1].disabled = True


def start_window():
    win.loop()