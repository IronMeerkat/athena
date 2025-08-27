FROM python:3.11-slim

# Copy requirements first to take advantage of Docker caching
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY . .

# Set environment defaults
ENV PYTHONUNBUFFERED=1

# Celery workers will be launched via docker-compose; no default CMD
CMD ["bash"]