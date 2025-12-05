# PyLearn Pro - Python 在线编程学习平台

**PyLearn Pro** 是一个轻量级、现代化的在线编程教育平台（OJ/IDE），专为 Python 教学和练习设计。它集成了基于 Web 的代码编辑器、安全的后端沙箱环境、自动评测系统以及 AI 智能助教功能。

-----

## ✨ 核心功能

  * **🐍 纯 Python 环境**：专注于 Python 语言的学习与评测，支持标准输入输出交互。
  * **💻 强大的 Web IDE**：集成 Microsoft Monaco Editor（VS Code 同款内核），支持语法高亮、自动补全和代码缩进。
  * **🛡️ 安全沙箱执行**：基于子进程（Subprocess）和临时文件机制运行用户代码，包含超时控制（防止死循环）和错误捕获。
  * **🤖 AI 智能助教**：集成大模型（DeepSeek/OpenAI）接口，提供代码纠错、思路提示和实时问答功能。
  * **📊 自动化评测**：支持自定义测试用例（输入/输出比对），实时反馈运行结果和正确性判定。
  * **⚙️ 后台管理系统**：
      * 题目增删改查（支持 Markdown 描述）。
      * 支持从 GitHub 仓库批量导入题目。
      * AI 辅助生成题目元数据（自动提取标题、难度、标签）。
      * Python 依赖库检查与一键安装。

-----

## 🛠️ 技术栈

  * **后端框架**: [FastAPI](https://fastapi.tiangolo.com/) (高性能异步 Web 框架)
  * **数据库**: SQLite (轻量级，无须额外配置)
  * **前端技术**: HTML5, JavaScript (原生), Jinja2 模板
  * **编辑器组件**: [Monaco Editor](https://microsoft.github.io/monaco-editor/)
  * **Markdown 渲染**: [Marked.js](https://marked.js.org/)
  * **依赖管理**: Python `pip`

-----

## 🚀 快速开始

### 1\. 环境要求

  * Python 3.9 或更高版本
  * 网络连接（用于加载 CDN 资源和调用 AI API）

### 2\. 安装依赖

在项目根目录下创建一个 `requirements.txt` 文件并填入以下内容，或直接运行安装命令：

```bash
pip install fastapi uvicorn jinja2 python-multipart openai bcrypt requests pydantic
```

### 3\. 项目配置

请确保项目根目录下存在 `config.py` 文件，并配置您的 AI API 密钥：

```python
# config.py
DB_NAME = "pylearn.db"

# 请替换为您的实际 API Key
AI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxx" 
AI_BASE_URL = "https://api.deepseek.com" # 或其他 OpenAI 兼容接口
AI_MODEL_NAME = "deepseek-coder"

SECRET_KEY = "your-secret-key-here"
```

### 4\. 启动服务

在终端中运行以下命令启动服务器：

```bash
python main.py
```

或者使用 `uvicorn` 热重载模式（开发推荐）：

```bash
uvicorn main:app --reload
```

启动成功后，访问：

  * **学生端 (IDE)**: `http://127.0.0.1:8000`
  * **管理后台**: `http://127.0.0.1:8000/login`

-----

## 📂 项目结构

```text
.
├── main.py              # FastAPI 主程序入口，路由定义
├── database.py          # 数据库模型与操作封装 (SQLite)
├── sandbox.py           # 代码沙箱，负责 Python 代码的安全执行
├── ai_service.py        # AI 接口封装 (出题、聊天、整理)
├── library_manager.py   # 依赖库检查与安装管理器
├── crawler.py           # GitHub 题目爬虫/导入工具
├── config.py            # 配置文件
├── requirements.txt     # 项目依赖列表
└── templates/           # 前端 HTML 模板
    ├── index.html       # 学生端 IDE 主界面
    ├── admin.html       # 管理员后台界面
    └── login.html       # 登录界面
```

-----

## 📝 使用指南

### 管理员 (Admin)

1.  **登录**：默认账号 `admin`，默认密码 `123456`。
2.  **添加题目**：点击“导入新题目”或在列表页点击编辑修改现有题目。支持设置题目描述、难度、知识点、时间限制及标准输入输出。
3.  **环境维护**：如果题目代码依赖第三方库（如 `numpy`），可在编辑弹窗中点击“检查依赖库”并一键安装。

### 学生 (Student)

1.  **选择题目**：在左侧列表选择题目。
2.  **编写代码**：在编辑器中编写 Python 代码。
3.  **运行/调试**：
      * 点击 **▶ 运行代码** 查看输出。
      * 在下方输入框填写 **程序输入 (Stdin)** 进行自定义测试。
      * 点击 **👀 对比答案** 查看参考代码（如果允许）。
4.  **AI 求助**：遇到报错或思路卡壳时，在左侧聊天框向 AI 提问。

-----

## ⚠️ 注意事项

  * **沙箱安全**：本项目使用 `subprocess` 进行基本的隔离，对于生产环境，建议将代码运行环境迁移至 Docker 容器中以获得更高的安全性。
  * **Windows 编码**：已内置 `PYTHONIOENCODING=utf-8` 环境变量配置，解决了 Windows 控制台下的中文乱码问题。

