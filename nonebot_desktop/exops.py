from glob import glob
import os
from pathlib import Path
import shlex
from shutil import which
import subprocess
import sys
from tempfile import mkstemp
from typing import Optional, Union
from venv import create as create_venv
from nb_cli.consts import WINDOWS
from nb_cli.handlers.project import create_project
from importlib import metadata
from dotenv.main import DotEnv


current_distros = metadata.distributions


def distributions(*fp: str):
    return metadata.distributions(path=list(fp))


def find_python(fp: Path):
    veexec = (
        fp / ".venv"
        / ("Scripts" if WINDOWS else "bin")
        / ("python.exe" if WINDOWS else "python")
    )
    return veexec if veexec.exists() else Path(sys.executable)


LINUX_TERMINALS = ("gnome-terminal", "konsole", "xfce4-terminal", "xterm", "st")


def get_terminal_starter():
    if WINDOWS:
        return ("start", "cmd.exe", "/c")
    for te in LINUX_TERMINALS:
        if which(te) is not None:
            return (te, "-e")
    raise FileNotFoundError("no terminal emulator found")


def get_terminal_starter_pure():
    if WINDOWS:
        return ("start", "cmd.exe")
    for te in LINUX_TERMINALS:
        if which(te) is not None:
            return (te,)
    raise FileNotFoundError("no terminal emulator found")


def get_pause_cmd():
    if WINDOWS:
        return "pause"
    return "read -n1 -p 进程已结束，按任意键关闭。"


def create(fp: str, drivers: list, adapters: list, dev: bool, usevenv: bool, index: Optional[str] = None):
    p = Path(fp)
    if p.exists():
        p.rmdir()
    create_project(
        "simple" if dev else "bootstrap",
        {
            "nonebot": {
                "project_name": p.name,
                "drivers": [d.dict() for d in drivers],
                "adapters": [a.dict() for a in adapters],
                "use_src": True
            }
        },
        str(p.parent)
    )
    dri_real = [d.project_link for d in drivers]
    adp_real = [a.project_link for a in adapters]
    dir_name = p.name.replace(" ", "-")
    venv_dir = p / ".venv"

    if usevenv:
        create_venv(venv_dir, prompt=dir_name, with_pip=True)

    pyexec = find_python(p)

    ret = subprocess.run(
        [pyexec, "-m", "pip", "install", *(("-i", index) if index else ()), "-U", "nonebot2", *dri_real, *adp_real]
    )
    if ret.returncode != 0:
        raise OSError("cannot install packages")


def gen_run_script(cwd: Path, cmd: str):
    fd, fp = mkstemp(".bat" if WINDOWS else ".sh", "nbdtk-")
    if not WINDOWS:
        os.chmod(fd, 0o755)
    with open(fd, "w") as f:
        if not WINDOWS:
            f.write(f"#!/usr/bin/env bash\n")

        if (cwd / ".venv").exists():
            if WINDOWS:
                f.write(f"{cwd / '.venv' / 'bin' / 'activate.bat'}\n")
            else:
                f.write(f"source {cwd / '.venv' / 'bin' / 'activate'}\n")

        f.write(f"cd \"{cwd}\"\n")
        f.write(f"{cmd}\n")
        f.write(f"{get_pause_cmd()}\n")
    return fp


def exec_new_win(cwd: Path, cmd: str):
    sname = gen_run_script(cwd, cmd)
    return subprocess.Popen(shlex.join((*get_terminal_starter(), sname)), shell=True), sname


def open_new_win(cwd: Path):
    subprocess.Popen(shlex.join(get_terminal_starter_pure()), shell=True, cwd=cwd)


def system_open(fp: Union[str, Path]):
    subprocess.Popen(shlex.join(("start" if WINDOWS else "xdg-open", str(fp))), shell=True)


def find_env_file(fp: Union[str, Path]):
    return glob(".env*", root_dir=fp)


def get_env_config(ep: Path, config: str):
    return DotEnv(ep).get(config)


def recursive_find_env_config(fp: Union[str, Path], config: str):
    pfp = Path(fp)
    cp = pfp / ".env"
    if not cp.is_file():
        return get_env_config(pfp / ".env.prod", config)
    glb = DotEnv(cp).dict()
    if config in glb:
        return glb[config]
    env = glb.get("ENVIRONMENT", None)
    return env and get_env_config(pfp / f".env.{env}", config)


def recursive_update_env_config(fp: Union[str, Path], config: str, value: str):
    pfp = Path(fp)
    cp = pfp / ".env"
    if not cp.is_file():
        cp = pfp / ".env.prod"
        useenv = DotEnv(cp).dict()
    else:
        useenv = DotEnv(cp).dict()
        if config not in useenv:
            env = get_env_config(cp, "ENVIRONMENT")
            if env:
                cenv = DotEnv(pfp / f".env.{env}").dict()
                if config in cenv:
                    cp = pfp / f".env.{env}"
                    useenv = cenv

    useenv.update({config: value})

    with open(cp, "w") as f:
        f.writelines(f"{k}={v}\n" for k, v in useenv.items() if k and v)