import json
from openai import OpenAI
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL_NAME

class AIService:
    def __init__(self):
        if AI_BASE_URL:
            self.client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        else:
            self.client = OpenAI(api_key=AI_API_KEY)
        self.model = AI_MODEL_NAME

    def generate_problem_metadata(self, code_content):
        """
        ETL: 强制 AI 生成包含 Markdown 代码块示例的描述
        """
        prompt = f"""
        你是一个严谨的Python算法题出题专家。请分析下面的代码，将其转化为一道标准的编程练习题。

        【目标代码】:
        {code_content}

        【任务要求】:
        请返回严格的 JSON 格式，必须包含以下字段：

        1. title: (字符串) 题目标题。
        2. description: (字符串) 题目详细描述，支持 Markdown。
           - 必须包含 "### 题目描述"。
           - 必须包含 "### 示例" 章节。
           - 【重要】在示例章节中，**必须**将输入和输出分开展示，并使用 bash 代码块格式(bash前和输入输出后的```不可忘记)，以便前端正确渲染多行数据。格式如下：
             **输入示例:**
             ```bash
             3
             10 20 30
             ```
             **输出示例:**
             ```bash
             60
             ```
           - 如果有复杂交互，请在描述文字中说明，但"输入/输出示例"只需展示核心数据。

        3. input: (字符串) 提取出的测试输入数据（用于后台评测）。如果有换行，请用 "\\n" 表示（例如 "3\\n10 20 30"）。
        4. output: (字符串) 代码在上述输入下的标准期望输出。
        5. difficulty: (整数) 1-5。
        6. knowledge: (字符串) 知识点，逗号分隔。
        """
        
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个严格输出JSON的数据处理助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = resp.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"ETL Error: {e}")
            return None

    def chat(self, user_msg, context):
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是Python助教。请根据上下文回答问题。"},
                    {"role": "user", "content": f"上下文:{context}\n问题:{user_msg}"}
                ]
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"连接失败: {e}"

    def cluster_problems(self, problems_summary):
        prompt = f"""
        对以下题目进行知识点归类，统一相同的标签。
        题目列表: {json.dumps(problems_summary, ensure_ascii=False)}
        请返回 JSON 格式: {{"题目ID": "统一后的标签名", ...}}
        """
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            content = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            return {}

ai = AIService()