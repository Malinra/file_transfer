import json
import os
import secrets
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "18000"))
USERS_FILE = Path(os.environ.get("USERS_FILE", BASE_DIR / "users.json")).resolve()
# 会话有效期（秒），默认 12 小时
SESSION_TTL = int(os.environ.get("SESSION_TTL", str(12 * 3600)))

app = Flask(__name__, static_folder=None)

# 内存会话表：token -> {"user": 用户名, "exp": 过期时间}
SESSIONS: dict[str, dict] = {}


# ------------------------------------------------------------------ 用户数据
def load_users() -> dict:
    """读取 users.json。结构:
    {
      "admin": {
        "password_hash": "...",
        "roots": ["/home/charlie"],   # 允许访问的目录
        "role": "admin"               # admin=可写, viewer=只读
      }
    }
    """
    if not USERS_FILE.exists():
        sys.exit(
            f"未找到用户文件 {USERS_FILE}\n"
            f"请先运行:  python manage_users.py add <用户名> <密码> <角色> <目录1,目录2...>"
        )
    with open(USERS_FILE, encoding="utf-8") as f:
        return json.load(f)


USERS = load_users()


def user_roots(username: str) -> list:
    info = USERS.get(username, {})
    return [Path(p).expanduser().resolve() for p in info.get("roots", [])]


def is_admin(username: str) -> bool:
    return USERS.get(username, {}).get("role") == "admin"


# ------------------------------------------------------------------ 会话
def new_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"user": username, "exp": time.time() + SESSION_TTL}
    return token


def current_user():
    token = request.headers.get("X-Token", "")
    sess = SESSIONS.get(token)
    if not sess:
        return None
    if sess["exp"] < time.time():
        SESSIONS.pop(token, None)
        return None
    return sess["user"]


# ------------------------------------------------------------------ 路径安全
def clean_parts(rel: str):
    """把相对路径拆成安全的片段, 拒绝 .. 和绝对路径技巧。"""
    parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
    for p in parts:
        if p == ".." or "\0" in p:
            raise ValueError("非法路径")
    return parts


def get_root_for(username: str, raw: str) -> Path:
    """根据当前用户的授权目录，确定并校验本次操作的根目录。"""
    allowed = user_roots(username)
    if not allowed:
        raise ValueError("该账号未配置可访问目录")
    chosen = Path(raw).expanduser().resolve() if raw else allowed[0]
    for base in allowed:
        if chosen == base or base in chosen.parents:
            return chosen
    raise ValueError("该根目录不在您的权限范围内")


def safe_path(root: Path, rel: str) -> Path:
    target = root.joinpath(*clean_parts(rel)).resolve()
    if target != root and root not in target.parents:
        raise ValueError("路径越界")
    return target


# ------------------------------------------------------------------ 鉴权钩子
PUBLIC_PATHS = {"/api/login"}


@app.before_request
def check_auth():
    if not request.path.startswith("/api/"):
        return None
    if request.path in PUBLIC_PATHS:
        return None
    if current_user() is None:
        return jsonify(error="未登录或会话已过期"), 401
    return None


@app.errorhandler(ValueError)
def bad_request(e):
    return jsonify(error=str(e)), 400


# ------------------------------------------------------------------ 路由
@app.get("/")
def index():
    return send_from_directory(Path(__file__).parent / "static", "index.html")


@app.get("/static/<path:fname>")
def static_files(fname):
    """提供前端静态资源（背景图等），无需登录。"""
    return send_from_directory(Path(__file__).parent / "static", fname)


@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")
    info = USERS.get(username)
    if not info or not check_password_hash(info.get("password_hash", ""), password):
        return jsonify(error="账号或密码错误"), 401
    token = new_session(username)
    return jsonify(
        token=token,
        username=username,
        role=info.get("role", "viewer"),
        roots=[str(p) for p in user_roots(username)],
    )


@app.post("/api/logout")
def logout():
    SESSIONS.pop(request.headers.get("X-Token", ""), None)
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    u = current_user()
    info = USERS.get(u, {})
    return jsonify(
        username=u,
        role=info.get("role", "viewer"),
        roots=[str(p) for p in user_roots(u)],
    )


@app.get("/api/roots")
def roots():
    u = current_user()
    allowed = user_roots(u)
    return jsonify(
        roots=[str(p) for p in allowed],
        default=str(allowed[0]) if allowed else "",
        allow_any=False,
    )


@app.get("/api/list")
def list_dir():
    u = current_user()
    root = get_root_for(u, request.args.get("root", ""))
    d = safe_path(root, request.args.get("path", ""))
    if not d.is_dir():
        return jsonify(error="目录不存在"), 404
    dirs, files = [], []
    for p in sorted(d.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith("."):  # 隐藏以 . 开头的文件/文件夹
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        if p.is_dir():
            dirs.append({"name": p.name})
        else:
            files.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime})
    return jsonify(
        root=str(root),
        path="/".join(clean_parts(request.args.get("path", ""))),
        dirs=dirs,
        files=files,
        can_write=is_admin(u),
    )


@app.post("/api/mkdir")
def mkdir():
    u = current_user()
    if not is_admin(u):
        return jsonify(error="只读账号无权限"), 403
    data = request.get_json(force=True)
    root = get_root_for(u, data.get("root", ""))
    if not clean_parts(data.get("name", "")):
        raise ValueError("目录名不能为空")
    target = safe_path(root, data.get("path", "") + "/" + data["name"])
    target.mkdir(parents=True, exist_ok=True)
    return jsonify(ok=True)


@app.post("/api/upload")
def upload():
    u = current_user()
    if not is_admin(u):
        return jsonify(error="只读账号无权限"), 403
    f = request.files.get("file")
    if f is None:
        raise ValueError("缺少文件")
    root = get_root_for(u, request.form.get("root", ""))
    base = request.form.get("path", "")
    rel = request.form.get("relpath") or f.filename or ""
    if not clean_parts(rel):
        raise ValueError("文件名为空")
    dest = safe_path(root, base + "/" + rel)
    if dest == root:
        raise ValueError("非法文件名")
    if dest.exists() and request.form.get("overwrite") != "1":
        return jsonify(error="文件已存在"), 409
    if dest.is_dir():
        return jsonify(error="同名目录已存在"), 409
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    f.save(tmp)
    os.replace(tmp, dest)
    return jsonify(ok=True)


if __name__ == "__main__":
    print(f"用户文件: {USERS_FILE}")
    print(f"已加载账号: {', '.join(USERS.keys())}")
    print(f"访问: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True)
