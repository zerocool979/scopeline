FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data HOME=/home/app
# LibreOffice (headless) dipakai untuk konversi DOCX -> PDF
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app && mkdir /data && chown app /data
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request as u;u.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
