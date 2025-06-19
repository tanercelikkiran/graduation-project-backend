# Python 3.10 tabanlı bir imaj kullan
FROM python:3.10

# Çalışma dizinini belirle
WORKDIR /app

# Bağımlılıkları yüklemek için ortam değişkenlerini ayarla
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Bağımlılık dosyalarını kopyala ve yükle
COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY main.py /app/
COPY src /app/src
EXPOSE 8000 

# .env dosyasını kopyala
COPY .env /app/.env

# FastAPI uygulamasını başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
