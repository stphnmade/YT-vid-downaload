FROM python:3.11-slim

WORKDIR /app

COPY services/downloader/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/downloader/app app
COPY services/downloader/yt-dlp.conf yt-dlp.conf

EXPOSE 4545

ENV YT_DOWNLOADER_HOST=0.0.0.0

CMD ["python", "app/server.py"]
