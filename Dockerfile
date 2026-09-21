FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY openapi ./openapi
COPY mcp ./mcp
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["uvicorn", "src.pamf.app:app", "--host", "0.0.0.0", "--port", "8080"]
