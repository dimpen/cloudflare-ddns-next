FROM python:alpine AS base

################################
FROM base AS builder

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


###############################
FROM base AS final

# Create non-root user
RUN addgroup -g 1000 -S appgroup && adduser -u 1000 -S appuser -G appgroup

COPY --from=builder /install /usr/local

WORKDIR /cf-ddns-next

RUN mkdir -p /data/logs /data/tmp && chown -R appuser:appgroup /data

COPY --chown=appuser:appgroup src/* .

USER appuser

ENTRYPOINT ["python", "-u", "main.py", "--config", "/config.json", "--docker"]
