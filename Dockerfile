FROM python:3.12-alpine

LABEL maintainer="TCE Manutenção Predial"
LABEL app="rfid"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=rfid \
    APP_PORT=5000

# Dependências para mysql-connector-python
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN if [ -f "pyproject.toml" ]; then pip install --no-cache-dir -e .; fi

RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

RUN mkdir -p /var/softwaresTCE/rfid/dados \
             /var/softwaresTCE/rfid/logs && \
    chown -R appuser:appuser /var/softwaresTCE /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "RFID:app"]
