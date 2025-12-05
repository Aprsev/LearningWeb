import os
import shutil
import tempfile
import subprocess
import glob
from database import db
from ai_service import ai

class RepoCrawler:
    def __init__(self):
        self.is_busy = False
        self.logs = [] 
        self.temp_repo_path = None 
        self.found_files = []

    def add_log(self, msg):
        print(f"[Crawler] {msg}")
        self.logs.append(msg)

    def scan_structure(self, repo_url):
        """Step 1: 仅下载代码，列出文件"""
        if self.is_busy: return
        self.is_busy = True
        self.logs = []
        self.found_files = []
        
        # 清理旧数据
        if self.temp_repo_path and os.path.exists(self.temp_repo_path):
            shutil.rmtree(self.temp_repo_path, ignore_errors=True)

        self.temp_repo_path = tempfile.mkdtemp()
        
        try:
            self.add_log(f"正在连接仓库: {repo_url}")
            subprocess.run(["git", "clone", "--depth", "1", repo_url, self.temp_repo_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 扫描 py 文件
            all_py_files = glob.glob(os.path.join(self.temp_repo_path, "**/*.py"), recursive=True)
            
            for f_path in all_py_files:
                if "__init__.py" in f_path or "setup.py" in f_path: continue
                # 过滤过小或过大的文件
                if os.path.getsize(f_path) < 20 or os.path.getsize(f_path) > 30000: continue
                
                rel_path = os.path.relpath(f_path, self.temp_repo_path)
                self.found_files.append(rel_path)
            
            self.add_log(f"✅ 扫描完成! 发现 {len(self.found_files)} 个文件。请选择需要导入的文件。")
            
        except Exception as e:
            self.add_log(f"❌ 扫描出错: {str(e)}")
            self.temp_repo_path = None
        finally:
            self.is_busy = False

    def process_selected(self, selected_indices):
        """Step 2: 对选中的文件进行 AI 分析"""
        if self.is_busy: return
        self.is_busy = True
        
        total = len(selected_indices)
        self.add_log(f"开始 AI 分析 {total} 个文件...")
        
        try:
            success_count = 0
            for i, idx in enumerate(selected_indices):
                if idx < 0 or idx >= len(self.found_files): continue
                
                rel_path = self.found_files[idx]
                full_path = os.path.join(self.temp_repo_path, rel_path)
                
                self.add_log(f"[{i+1}/{total}] 分析中: {rel_path}")
                
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    
                    meta = ai.generate_problem_metadata(code)
                    
                    if meta and isinstance(meta, dict):
                        # 数据清洗
                        if isinstance(meta.get('knowledge'), list):
                            meta['knowledge'] = ", ".join(str(x) for x in meta['knowledge'])
                        if not meta.get('knowledge'): meta['knowledge'] = "综合"
                        
                        meta['source_repo'] = "Git Import"
                        meta['file_path'] = rel_path
                        meta['code'] = code
                        
                        # 1. 保存题目主体 (这部分逻辑微调，获取插入后的 ID)
                        # 注意：你需要修改 add_problem_from_crawler 让它返回 ID，或者先查 ID
                        db.add_problem_from_crawler(meta)
                        
                        # 获取刚刚插入的题目 ID
                        conn = db.get_conn()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM problems WHERE source_repo=? AND file_path=?", (meta['source_repo'], meta['file_path']))
                        pid = cursor.fetchone()[0]
                        conn.close()

                        # 2. 【新增】保存多组测试用例
                        # 先清空旧的（防止重复导入时堆积）
                        db.clear_test_cases(pid)
                        
                        # 如果 AI 生成了 test_cases 列表
                        if 'test_cases' in meta and isinstance(meta['test_cases'], list):
                            for case in meta['test_cases']:
                                # 确保输入数据最后有换行符，防止 EOFError
                                inp = case.get('input', '')
                                out = case.get('output', '')
                                
                                # 技巧：处理多行输入。
                                # 如果程序有多个 input()，数据库存的数据必须是 "Line1\nLine2"
                                # 这里的 inp 应该是 AI 生成好的带 \n 的字符串
                                
                                db.add_test_case(pid, inp, out)
                                
                            print(f"✅ 已保存 {len(meta['test_cases'])} 组测试数据")
                        else:
                            # 兼容旧逻辑：如果 AI 没生成数组，用单组数据兜底
                            db.add_test_case(pid, meta.get('input', ''), meta.get('output', ''))

                        success_count += 1
                    else:
                        self.add_log(f"⚠️ 跳过 {rel_path}: AI 数据生成失败")
                        
                except Exception as e:
                    print(f"File Error: {e}")
            
            self.add_log(f"🎉 全部完成! 成功入库: {success_count} 题。")
            
        except Exception as e:
            self.add_log(f"❌ 流程中断: {e}")
        finally:
            # 完成后清理
            if self.temp_repo_path and os.path.exists(self.temp_repo_path):
                shutil.rmtree(self.temp_repo_path, ignore_errors=True)
                self.temp_repo_path = None
                self.found_files = []
            self.is_busy = False

    def organize_database(self):
        self.is_busy = True
        self.logs.append("开始整理知识点...")
        try:
            all_probs = db.get_all_problems()
            summary = [{"id": p["id"], "title": p["title"]} for p in all_probs]
            updates = ai.cluster_problems(summary)
            if updates:
                db.update_knowledge_tags(updates)
                self.logs.append(f"✅ 整理完成，更新 {len(updates)} 条。")
        finally:
            self.is_busy = False

crawler_service = RepoCrawler()