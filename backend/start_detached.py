"""Inicia o runserver do Atlas como um processo desanexado (persistente).

Uso:  python start_detached.py
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Flags do Windows: CREATE_NEW_PROCESS_GROUP (0x200) + DETACHED_PROCESS (0x8)
DETACHED = 0x00000008 | 0x00000200

log = open(os.path.join(BASE, "runserver.log"), "w", encoding="utf-8")
err = open(os.path.join(BASE, "runserver.err.log"), "w", encoding="utf-8")

p = subprocess.Popen(
    [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
    cwd=BASE,
    stdout=log,
    stderr=err,
    stdin=subprocess.DEVNULL,
    creationflags=DETACHED,
    close_fds=True,
)
print(f"PID={p.pid}")
