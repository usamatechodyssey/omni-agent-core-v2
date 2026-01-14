# Dockerfile for Python FastAPI Application
# 1. Base Image 
FROM python:3.11-slim 

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    python3-dev \
    gcc \
    libgomp1 \ 
    && rm -rf /var/lib/apt/lists/*

# 4. Set Work Directory
WORKDIR /app

# 5. Install Dependencies (Layer Caching Strategy)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt --default-timeout 1000 \
    --extra-index-url https://download.pytorch.org/whl/cpu

# 6. Copy Application Code
COPY . .

# --- 🔥 FIX: PYTHONPATH ADDED 🔥 ---
# Ye Python ko batata hai ke 'backend' folder root mein hai
ENV PYTHONPATH=/app:$PYTHONPATH 

# 7. Expose Port
EXPOSE 8000

# 8. Run Command (Universal Logic)
# Yeh check karega: Agar server ne PORT diya hai to wo use karo, warna 8000 use karo.
CMD uvicorn backend.src.main:app --host 0.0.0.0 --port ${PORT:-8000}
