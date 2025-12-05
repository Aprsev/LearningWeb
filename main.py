from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import List

from database import db
from sandbox import Sandbox
from ai_service import ai
from crawler import crawler_service
from library_manager import lib_manager

app = FastAPI(title="PyLearn AI Platform")

# --- 安全中间件配置 ---
# ⚠️ 生产环境请修改 secret_key 为随机长字符串
app.add_middleware(SessionMiddleware, secret_key="YOUR_SUPER_SECRET_KEY")

templates = Jinja2Templates(directory="templates")

# --- Pydantic Models ---
class RunRequest(BaseModel):
    problem_id: int
    code: str

class ChatRequest(BaseModel):
    message: str
    problem_id: int
    code_context: str = ""
    error_context: str = ""

class ScanRequest(BaseModel):
    url: str

class ImportRequest(BaseModel):
    indices: List[int]

class UpdateProblemRequest(BaseModel):
    id: int
    title: str
    description: str
    difficulty: int
    category: str
    code: str
    time_limit: int =2

class InstallLibRequest(BaseModel):
    lib_name: str

# --- 鉴权依赖 ---
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

def admin_required(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=302, detail="Unauthorized", headers={"Location": "/login"})
    return user

# --- 核心逻辑补充：标准化输出函数 ---
def normalize_output(text: str) -> str:
    """
    标准化输出结果，用于对比答案：
    1. 统一换行符 (\r\n -> \n)
    2. 去除首尾空白
    3. (可选) 清理可能存在的 markdown 代码块标记，防止 AI 生成的数据带格式导致判错
    """
    if not text:
        return ""
    
    # 基础清洗
    text = text.strip().replace("\r\n", "\n")
    
    # 容错处理：如果数据库中的 expected_output 包含了 markdown 标记 (```text ... ```)
    # 我们尝试剥离它
    if text.startswith("```"):
        lines = text.splitlines()
        # 如果是多行且首尾都是 ```，则取中间内容
        if len(lines) >= 2 and "```" in lines[-1]:
            text = "\n".join(lines[1:-1])
            
    return text.strip()

# --- 登录页面 & API ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login_action")
async def login_action(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if db.authenticate_user(form_data.username, form_data.password):
        request.session["user"] = form_data.username
        return RedirectResponse(url="/admin", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "用户名或密码错误"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

# --- 开放路由 (学员端) ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    problems = db.get_all_problems()
    user = request.session.get("user")
    return templates.TemplateResponse("index.html", {"request": request, "problems": problems, "user": user})

@app.get("/problem/{pid}")
async def get_problem(pid: int):
    detail = db.get_problem_detail(pid)
    return {"detail": detail}

@app.post("/run")
async def run_code(req: RunRequest):
    # --- 🟢 [修改开始] 数据获取适配部分 🟢 ---
    
    # 1. 从数据库获取单组测试数据和时间限制
    # 注意：这里调用的是 database.py 中修改后的 get_test_data，它返回 (input, output, time_limit)
    # 这样就能获取到 time_limit 变量，供下面的 Sandbox.run 使用
    db_input, db_output, time_limit = db.get_test_data(req.problem_id)
    
    # 2. 将单组数据封装成列表，适配下方的循环逻辑
    # (如果未来您实现了 get_test_cases，可以直接替换这里)
    cases = [{"input": db_input, "output": db_output}]
    
    # 判空保护：如果数据库里完全没数据，给一个默认空输入
    if not db_input and not db_output:
         cases = [{"input": "\n", "output": ""}]
    
    # --- 🟢 [修改结束] 下面完全保留您的循环逻辑 🟢 ---

    total_cases = len(cases)
    passed_cases = 0
    first_error = None
    first_output = None 
    
    print(f"🚀 开始判题 ID:{req.problem_id}, 共 {total_cases} 个测试点")

    # 3. 循环判题
    for idx, case in enumerate(cases):
        # 预处理输入
        real_input = case['input'].replace('\\n', '\n') if case['input'] else ""
        
        # 运行沙箱 (🟢 此时 time_limit 变量已在上面定义，不会报错了)
        result = Sandbox.run(req.code, real_input, timeout=time_limit)
        
        # 记录第一组输出
        if idx == 0:
            first_output = result["stdout"]
            if result["status"] != "success":
                return {
                    "output": result["stdout"],
                    "error": result["stderr"],
                    "is_correct": False,
                    "expected": "Runtime Error"
                }

        # 标准化对比
        user_out = normalize_output(result["stdout"])
        std_out = normalize_output(case['output'])
        
        if user_out == std_out:
            passed_cases += 1
        else:
            if first_error is None:
                first_error = {
                    "case_idx": idx + 1,
                    "input": case['input'],
                    "user_out": user_out,
                    "expected": std_out
                }

    # 4. 汇总结果
    is_all_correct = (passed_cases == total_cases)
    
    response_data = {
        "output": first_output, 
        "is_correct": is_all_correct,
        "error": "",
        "expected": ""
    }

    if is_all_correct:
        response_data["expected"] = "All Passed"
        db.save_submission(req.problem_id, req.code, first_output, "", True, "")
    else:
        err_msg = f"❌ 未通过。成功: {passed_cases}/{total_cases}。\n"
        if first_error:
            err_msg += f"在第 {first_error['case_idx']} 组数据出错。\n"
            err_msg += f"输入: {first_error['input']}\n"
            err_msg += f"你的输出: {first_error['user_out']}\n"
            err_msg += f"期望输出: {first_error['expected']}"
        
        response_data["error"] = err_msg
        response_data["expected"] = first_error['expected'] if first_error else ""
        
        db.save_submission(req.problem_id, req.code, first_output, err_msg, False, "")

    return response_data

@app.post("/chat")
async def chat_with_ai(req: ChatRequest):
    detail = db.get_problem_detail(req.problem_id)
    context = f"当前题目：{detail['title']}\n"
    if req.code_context: context += f"\n用户代码：\n{req.code_context}\n"
    if req.error_context: context += f"\n报错：\n{req.error_context}\n"
    reply = ai.chat(req.message, context)
    return {"reply": reply}

# --- 管理路由 (需要鉴权) ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    try:
        admin_required(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=302)
    
    problems = db.get_all_problems()
    return templates.TemplateResponse("admin.html", {"request": request, "problems": problems, "user": request.session.get("user")})

@app.post("/admin/scan")
async def start_scan(req: ScanRequest, bg_tasks: BackgroundTasks, user=Depends(admin_required)):
    if crawler_service.is_busy: return {"status": "busy", "msg": "忙碌中"}
    bg_tasks.add_task(crawler_service.scan_structure, req.url)
    return {"status": "ok"}

@app.get("/admin/scan_status")
async def get_scan_status(user=Depends(admin_required)):
    files = []
    for i, f in enumerate(crawler_service.found_files): files.append({"index": i, "path": f})
    return {"is_busy": crawler_service.is_busy, "logs": crawler_service.logs, "files": files, "has_repo": crawler_service.temp_repo_path is not None}

@app.post("/admin/import")
async def process_files(req: ImportRequest, bg_tasks: BackgroundTasks, user=Depends(admin_required)):
    if crawler_service.is_busy: return {"status": "busy"}
    bg_tasks.add_task(crawler_service.process_selected, req.indices)
    return {"status": "ok"}

@app.post("/admin/update_problem")
async def update_problem_api(req: UpdateProblemRequest, user=Depends(admin_required)):
    db.update_problem_details(req.id, {
        "title": req.title, 
        "description": req.description, 
        "difficulty": req.difficulty, 
        "category": req.category, 
        "code": req.code,
        "time_limit": req.time_limit
    })
    return {"status": "ok"}

@app.post("/admin/delete/{pid}")
async def delete_problem(pid: int, user=Depends(admin_required)):
    db.delete_problem(pid)
    return {"status": "ok"}

# --- 库管理接口 ---

@app.post("/admin/check_dependencies")
async def check_dependencies(req: RunRequest, user=Depends(admin_required)):
    imports = lib_manager.get_imports(req.code)
    missing = lib_manager.check_missing_libs(imports)
    return {"missing": list(missing)}

@app.post("/admin/install_lib")
async def install_lib(req: InstallLibRequest, user=Depends(admin_required)):
    success, msg = lib_manager.install_lib(req.lib_name)
    if success:
        return {"status": "ok", "msg": f"{req.lib_name} 安装成功"}
    else:
        return {"status": "error", "msg": f"安装失败: {msg}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)