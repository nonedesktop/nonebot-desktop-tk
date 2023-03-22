from pathlib import Path
import subprocess
import sys
from venv import create as create_venv
from nb_cli.consts import WINDOWS
from nb_cli.handlers.project import create_project


def create(fp: str, drivers: list, adapters: list, dev: bool, usevenv: bool):
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
    pyexec = sys.executable

    if usevenv:
        create_venv(venv_dir, prompt=dir_name, with_pip=True)
        pyexec = (
            venv_dir
            / ("Scripts" if WINDOWS else "bin")
            / ("python.exe" if WINDOWS else "python")
        )

    ret = subprocess.run(
        [pyexec, "-m", "pip", "install", "-U", "nonebot2", *dri_real, *adp_real]
    )
    if ret.returncode != 0:
        raise OSError("cannot install packages")