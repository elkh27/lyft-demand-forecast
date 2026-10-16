FROM python:3.11-slim

# لایت‌جی‌بی‌ام در لینوکس به این کتابخانه نیاز داره (معادل libomp مک)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY app/ app/
COPY models/lgbm_demand.txt models/
COPY serving/ serving/

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]