FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    nbclient==0.10.2 nbformat==5.10.4 ipykernel==6.29.5
COPY docker/phase20-notebook-runner/execute.py /runner/execute.py
RUN chmod 0555 /runner/execute.py
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python", "/runner/execute.py"]
