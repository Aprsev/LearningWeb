import ast
import sys
import subprocess
import importlib.util

class LibraryManager:
    # --- 新增：常用库的 import 名到 pip 包名的映射 ---
    PKG_MAPPING = {
        "wx": "wxPython",
        "cv2": "opencv-python",
        "sklearn": "scikit-learn",
        "PIL": "Pillow",
        "yaml": "PyYAML",
        "bs4": "beautifulsoup4",
        "usb": "pyusb",
        "serial": "pyserial",
        "dotenv": "python-dotenv"
    }

    @staticmethod
    def get_imports(code: str):
        """解析代码中的所有 import 库名"""
        try:
            tree = ast.parse(code)
        except:
            return set()

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        return imports

    @staticmethod
    def check_missing_libs(imports: set):
        """检查哪些库在当前环境中未安装"""
        missing = []
        for lib in imports:
            # 排除 Python 内置库
            if lib in sys.builtin_module_names:
                continue

            try:
                # 尝试查找模块规格
                spec = importlib.util.find_spec(lib)
                if spec is None:
                    missing.append(lib)
            except:
                # 如果查找出错，也视为缺失，等待后续安装时处理
                missing.append(lib)
        return missing

    @staticmethod
    def install_lib(lib_name: str):
        """调用 pip 安装库 (支持别名映射)"""
        
        # 1. 查表获取真实的 pip 包名
        # 如果 lib_name 在映射表中，取映射值；否则默认使用 lib_name
        real_pkg_name = LibraryManager.PKG_MAPPING.get(lib_name, lib_name)

        print(f"Installing: {lib_name} -> {real_pkg_name}...") # 打印日志方便调试

        try:
            # 2. 指定清华源或其他国内源可加速下载 (可选，如果服务器在海外可去掉 -i 参数)
            # subprocess.check_call([sys.executable, "-m", "pip", "install", real_pkg_name, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
            
            # 使用默认源安装
            subprocess.check_call([sys.executable, "-m", "pip", "install", real_pkg_name])
            
            return True, f"Success ({real_pkg_name})"
        except subprocess.CalledProcessError:
            return False, f"Installation Failed for '{real_pkg_name}'"
        except Exception as e:
            return False, str(e)

lib_manager = LibraryManager()