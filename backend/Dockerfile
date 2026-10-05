FROM python:3.12.9-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY requirements.lock ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && addgroup --system app && adduser --system --ingroup app app
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
