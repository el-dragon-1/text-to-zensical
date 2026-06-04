FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY README.md ./
COPY templates ./templates
COPY static ./static

RUN mkdir -p /data/exports

ENV OUTPUT_ROOT=/data/exports
ENV PORT=8000

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
