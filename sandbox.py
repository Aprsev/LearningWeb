import subprocess
import sys
import tempfile
import os

class Sandbox:
    @staticmethod
    def run(code: str, input_data: str, timeout: int = 2):
        """
        在临时文件中运行代码，捕获输出。
        返回: (stdout, stderr, status)
        """
        # 创建临时 Python 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # 1. 准备环境变量，强制指定 Python IO 编码为 UTF-8
            # 这能解决在 Windows (默认GBK) 或某些容器中 print 中文报错的问题
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            # 启动子进程执行代码
            process = subprocess.Popen(
                [sys.executable, tmp_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,     # 文本模式，自动解码
                env=env        # 注入环境变量
            )
            
            # 写入输入数据并获取输出（设置 3 秒超时防止死循环）
            stdout, stderr = process.communicate(input=input_data, timeout=timeout)
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "status": "success" if process.returncode == 0 else "runtime_error"
            }

        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except:
                pass
            return {"stdout": "", "stderr": f"Error: Execution Timeout ({timeout}s limit).", "status": "timeout"}
        except Exception as e:
            return {"stdout": "", "stderr": f"System Error: {str(e)}", "status": "system_error"}
        finally:
            # 清理临时文件
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass