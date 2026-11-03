FROM python:3.13-slim
WORKDIR /servico
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8100"]