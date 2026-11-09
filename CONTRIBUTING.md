# 贡献指南 (Contributing Guide)

感谢你对 **File Transfer** 项目的关注与支持！我们欢迎各类贡献，包括但不限于报告 Bug、提出新特性建议、完善文档以及提交代码。

---

## 1. 提交规范

### 1.1 分支管理
- `main`：稳定主分支，只接收经过验证的 Pull Request。
- `feature/*`：新功能开发分支。
- `fix/*`：缺陷修复分支。

### 1.2 Commit Message 格式
推荐遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
```text
<type>(<scope>): <subject>

<body>
```
常用类型：
- `feat`: 新增功能（如分片断点续传、文件下载打包等）
- `fix`: 修复缺陷（如路径遍历越界漏洞、并发上传冲突等）
- `docs`: 文档变动（如更新 README、PRD）
- `refactor`: 代码重构（不影响外部行为的结构优化）
- `perf`: 性能调优

示例：
- `feat(auth): add remember-me cookie session support`
- `fix(upload): resolve file locking conflict on Windows systems`
- `docs(readme): add docker deployment guide`

---

## 2. 本地开发与测试流程

1. **Fork 本仓库** 到个人 GitHub 账号。
2. **克隆分支**：
   ```bash
   git clone https://github.com/<your-username>/file_transfer.git
   cd file_transfer
   ```
3. **创建特性分支**：
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **安装依赖与配置**：
   ```bash
   pip install -r requirements.txt
   python file_transfer/manage_users.py add admin Admin@123 admin /tmp/shared
   ```
5. **本地启动测试**：
   ```bash
   bash start.sh
   ```
6. **安全自检**：
   - 确保没有提交私有 `users.json` 文件（包含真实密码哈希与主机路径）。
   - 确保没有提交本地生成的 `*.log` 或 `*.pid` 文件。
   - 验证路径穿越防御机制（测试包含 `..`、空字符或绝对路径的请求）。
7. **提交 Pull Request**：
   - 详细描述你的修改内容及测试验证结果。

---

## 3. 安全漏洞反馈

如发现任何潜在的安全漏洞（如未授权访问、目录逃逸等），请切勿通过公共 Issue 公开，请通过安全私信或直接联系维护者。
