#!/usr/bin/env python3
"""用户管理脚本

用法:
  列出用户:   python manage_users.py list
  添加/更新:  python manage_users.py add <用户名> <密码> <角色 admin|viewer> <目录1,目录2,...>
  删除用户:   python manage_users.py del <用户名>
  改密码:     python manage_users.py passwd <用户名> <新密码>

示例:
  python manage_users.py add admin  Admin@123  admin  /home/charlie
  python manage_users.py add alice  Alice@123  viewer /home/charlie/shared_files
"""
import json
import os
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = Path(os.environ.get("USERS_FILE", BASE_DIR / "users.json")).resolve()


def load() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"已写入 {USERS_FILE}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    users = load()

    if cmd == "list":
        if not users:
            print("(无用户)")
        for name, info in users.items():
            print(f"- {name}  角色={info.get('role')}  目录={info.get('roots')}")

    elif cmd == "add":
        if len(args) < 5:
            sys.exit("用法: add <用户名> <密码> <角色> <目录1,目录2,...>")
        name, pwd, role, roots = args[1], args[2], args[3], args[4]
        if role not in ("admin", "viewer"):
            sys.exit("角色只能是 admin 或 viewer")
        root_list = [str(Path(p).expanduser().resolve()) for p in roots.split(",") if p.strip()]
        users[name] = {
            "password_hash": generate_password_hash(pwd),
            "role": role,
            "roots": root_list,
        }
        save(users)
        print(f"账号 {name} 已保存 (角色={role}, 目录={root_list})")

    elif cmd == "passwd":
        if len(args) < 3:
            sys.exit("用法: passwd <用户名> <新密码>")
        name, pwd = args[1], args[2]
        if name not in users:
            sys.exit("用户不存在")
        users[name]["password_hash"] = generate_password_hash(pwd)
        save(users)
        print(f"账号 {name} 密码已更新")

    elif cmd == "del":
        if len(args) < 2:
            sys.exit("用法: del <用户名>")
        name = args[1]
        if users.pop(name, None) is None:
            sys.exit("用户不存在")
        save(users)
        print(f"账号 {name} 已删除")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
