FROM athena-infrastructure-base:latest

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

RUN chmod +x scripts/entrypoint_worker.sh

CMD ["bash", "-lc", "scripts/entrypoint_worker.sh"]