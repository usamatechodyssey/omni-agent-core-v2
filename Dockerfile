# 1. Base Image (Lightweight Python)
FROM  python:3.10-slim

# 2. Set Environment Variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr (logs show up immediately)
ENV PYTHONUNBUFFERED 1

# 3. Install System Dependencies
# 'build-essential' is often needed for compiling python packages like numpy/cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Set Work Directory
WORKDIR /app

# 5. Install Dependencies (Layer Caching Strategy)
# We copy requirements FIRST. If requirements don't change, Docker uses cached layer here.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 6. Copy Application Code
COPY . .

# 7. Expose Port
EXPOSE 8000

# 8. Run Command
# We use host 0.0.0.0 so it is accessible outside the container
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]