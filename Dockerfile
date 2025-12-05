# 1. 基础镜像：使用官方轻量级 Python 3.9
FROM python:3.9-slim

# 2. 设置容器内的时区为中国上海 (可选，方便看日志时间)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 3. 设置工作目录
WORKDIR /app

# 4. 优化 pip 下载源（使用清华源，大幅提升国内构建速度）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制依赖文件并安装
# 这里分步操作是为了利用 Docker 缓存，只有 requirements 变了才重新安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 预安装 Git (爬虫模块需要用)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 7. 复制项目所有代码到容器里
COPY . .

# 8. 暴露端口
EXPOSE 8000

# 9. 启动命令
CMD ["python", "main.py"]