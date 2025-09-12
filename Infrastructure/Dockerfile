FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY athena-utils /opt/athena-utils

RUN pip install --upgrade pip && pip install -e /opt/athena-utils && pip install sentence-transformers==5.1.0