FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    PYTHONPATH=/opt/notebook-runtime

WORKDIR /workspace

COPY notebook-sandbox/requirements.txt /opt/notebook-sandbox/requirements.txt
COPY core/security.py /opt/notebook-runtime/core/security.py
COPY scripts/notebook_validation.py /opt/notebook-runtime/scripts/notebook_validation.py
COPY scripts/notebook_read.py /opt/notebook-runtime/scripts/notebook_read.py
COPY scripts/notebook_container_runner.py /opt/notebook-runtime/scripts/notebook_container_runner.py

RUN touch /opt/notebook-runtime/core/__init__.py /opt/notebook-runtime/scripts/__init__.py \
    && python -m pip install --no-cache-dir -r /opt/notebook-sandbox/requirements.txt \
    && python -m ipykernel install --prefix=/usr/local --name python3 --display-name "Python 3" \
    && groupadd --system --gid 10001 notebookrunner \
    && useradd --system --uid 10001 --gid 10001 --home-dir /tmp --shell /usr/sbin/nologin notebookrunner \
    && mkdir -p /workspace/output \
    && chown -R 10001:10001 /workspace/output /tmp

USER 10001:10001

CMD ["python", "-m", "ipykernel", "--version"]
