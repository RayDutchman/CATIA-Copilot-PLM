FROM python:3.11-slim-bookworm

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 运行
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
