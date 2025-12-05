import sqlite3
import time
import bcrypt  # 🟢 改用原生 bcrypt
from config import DB_NAME

class Database:
    def __init__(self):
        self.db_path = DB_NAME
        self.init_db()

    def get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # 1. 题目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                difficulty INTEGER DEFAULT 1,
                knowledge_tag TEXT DEFAULT '未分类',
                sample_code TEXT,
                test_input TEXT,
                expected_output TEXT,
                time_limit INTEGER DEFAULT 2,  -- 🟢 新增字段
                source_repo TEXT,
                file_path TEXT,
                created_at REAL
            )
        ''')

        # 2. 提交记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER,
                code TEXT,
                user_output TEXT,
                error_msg TEXT,
                is_correct BOOLEAN,
                ai_analysis TEXT,
                created_at REAL
            )
        ''')

        # 3. 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                hashed_password TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER,
                input_data TEXT,
                output_data TEXT,
                is_sample BOOLEAN DEFAULT 0  -- 标记是否为展示给用户的样例
            )
        ''')
        
        # 创建默认管理员
        self._create_default_admin(cursor)

        conn.commit()
        conn.close()

        self._check_and_migrate()

    def _create_default_admin(self, cursor):
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            # 🟢 [修改] 使用原生 bcrypt 生成哈希
            # 1. encode('utf-8') 将字符串转为字节
            # 2. gensalt() 生成盐
            # 3. decode('utf-8') 将生成的哈希字节转回字符串存入数据库
            hashed = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", ("admin", hashed))
            print("🔒 [Security] 默认管理员已创建: admin / 123456")

    # --- 用户鉴权方法 ---
    def authenticate_user(self, username, password):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT hashed_password FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if not row: return False
        
        stored_hash = row[0]
        # 🟢 [修改] 使用原生 bcrypt 验证
        # checkpw 需要两个参数都是 bytes 类型
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except Exception as e:
            print(f"Auth Error: {e}")
            return False
    
    def _check_and_migrate(self):
        """简单的自动迁移脚本"""
        conn = self.get_conn()
        try:
            # 尝试查询该字段，如果报错说明不存在
            conn.execute("SELECT time_limit FROM problems LIMIT 1")
        except:
            print("⚠️ 检测到旧版数据库，正在添加 time_limit 字段...")
            conn.execute("ALTER TABLE problems ADD COLUMN time_limit INTEGER DEFAULT 2")
            conn.commit()
        finally:
            conn.close()
            
    # --- 写入接口 (保持不变) ---
    def add_problem_from_crawler(self, data):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM problems WHERE source_repo=? AND file_path=?", (data['source_repo'], data['file_path']))
        exist = cursor.fetchone()
        if exist:
            cursor.execute('''UPDATE problems SET title=?, description=?, difficulty=?, sample_code=?, test_input=?, expected_output=?, knowledge_tag=? WHERE id=?''', 
                           (data['title'], data['description'], data['difficulty'], data['code'], data['input'], data['output'], data['knowledge'], exist[0]))
        else:
            cursor.execute('''INSERT INTO problems (title, description, difficulty, sample_code, test_input, expected_output, knowledge_tag, source_repo, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                           (data['title'], data['description'], data['difficulty'], data['code'], data['input'], data['output'], data['knowledge'], data['source_repo'], data['file_path'], time.time()))
        conn.commit()
        conn.close()

    # --- 读取接口 (保持不变) ---
    def get_all_problems(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, knowledge_tag, difficulty, source_repo FROM problems ORDER BY difficulty ASC, id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "category": r[2], "difficulty": r[3], "source": r[4]} for r in rows]

    def get_problem_detail(self, pid):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM problems WHERE id=?", (pid,))
        row = cursor.fetchone()
        conn.close()
        if row:
            # 注意：row 的索引取决于你的建表顺序，建议用 row['time_limit'] 如果开启了 row_factory
            # 这里假设 time_limit 是第 8 列 (从0开始数，基于上面的 CREATE TABLE 顺序)
            # id(0), title(1), desc(2), diff(3), tag(4), code(5), input(6), output(7), limit(8)...
            # 为了稳妥，我们重新查一次或者在 SQL 里指定列名
            return {
                "id": row[0], 
                "title": row[1], 
                "description": row[2], 
                "difficulty": row[3], 
                "category": row[4], 
                "sample_code": row[5],
                "time_limit": row[8] if len(row) > 8 else 2 # 🟢 返回时间限制
            }
        return None
    
    def get_test_data(self, pid):
        conn = self.get_conn()
        # 🟢 顺便读出 time_limit
        res = conn.execute("SELECT test_input, expected_output, time_limit FROM problems WHERE id=?", (pid,)).fetchone()
        conn.close()
        if res:
            # 如果数据库里是 NULL (老数据)，默认给 2 秒
            t_limit = res[2] if res[2] else 2
            return res[0], res[1], t_limit
        return "", "", 2

    def save_submission(self, pid, code, output, error, is_correct, ai_analysis):
        conn = self.get_conn()
        conn.execute('''INSERT INTO submissions (problem_id, code, user_output, error_msg, is_correct, ai_analysis, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)''', (pid, code, output, error, is_correct, ai_analysis, time.time()))
        conn.commit()
        conn.close()

    def get_history(self, pid):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE problem_id=? ORDER BY id DESC LIMIT 5", (pid,))
        rows = cursor.fetchall()
        conn.close()
        return [{"date": time.strftime("%H:%M", time.localtime(r[7])), "is_correct": r[5]} for r in rows]

    def delete_problem(self, pid):
        conn = self.get_conn()
        conn.execute("DELETE FROM problems WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    def update_problem_details(self, pid, data):
        conn = self.get_conn()
        # 🟢 增加 time_limit 更新
        conn.execute('''UPDATE problems SET title=?, description=?, difficulty=?, knowledge_tag=?, sample_code=?, time_limit=? WHERE id=?''', 
                     (data['title'], data['description'], data['difficulty'], data['category'], data['code'], data['time_limit'], pid))
        conn.commit()
        conn.close()
        
    def update_knowledge_tags(self, updates):
        conn = self.get_conn()
        for pid, tag in updates.items():
            conn.execute("UPDATE problems SET knowledge_tag=? WHERE id=?", (tag, pid))
        conn.commit()
        conn.close()

    def add_test_case(self, pid, input_data, output_data, is_sample=False):
        conn = self.get_conn()
        conn.execute("INSERT INTO test_cases (problem_id, input_data, output_data, is_sample) VALUES (?, ?, ?, ?)", 
                     (pid, input_data, output_data, is_sample))
        conn.commit()
        conn.close()

    def get_test_cases(self, pid):
        """获取该题目的所有测试点"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT input_data, output_data FROM test_cases WHERE problem_id=?", (pid,))
        rows = cursor.fetchall()
        conn.close()
        return [{"input": r[0], "output": r[1]} for r in rows]

    def clear_test_cases(self, pid):
        """更新题目时先清空旧的测试点"""
        conn = self.get_conn()
        conn.execute("DELETE FROM test_cases WHERE problem_id=?", (pid,))
        conn.commit()
        conn.close()
        
db = Database()