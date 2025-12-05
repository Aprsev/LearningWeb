# config.py
import os

# --- AI 配置 ---
# 如果使用 OpenAI，base_url 不需要改。
# 如果使用国内模型（如 DeepSeek），请修改 BASE_URL 和 API_KEY。
AI_API_KEY = "c50ae10fcce54889bdb12cb8fa97e084.EHRaEbFBnyGJrkpE"  # 🔴 请在此处填入你的 API Key
AI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/" # 🔴 示例：DeepSeek 的 API 地址
AI_MODEL_NAME = "GLM-4.5-Flash"             # 🔴 模型名称

# --- 数据库配置 ---
DB_NAME = "pylearn.db"
