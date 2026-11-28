FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /workspace

COPY notebook-sandbox/requirements.txt /opt/notebook-sandbox/requirements.txt
RUN python -m pip install --no-cache-dir -r /opt/notebook-sandbox/requirements.txt \
    && groupadd --system --gid 10001 notebookrunner \
    && useradd --system --uid 10001 --gid 10001 --home-dir /tmp --shell /usr/sbin/nologin notebookrunner \
    && mkdir -p /workspace/output \
    && chown -R 10001:10001 /workspace/output /tmp

USER 10001:10001

CMD ["python", "-m", "ipykernel", "--version"]
