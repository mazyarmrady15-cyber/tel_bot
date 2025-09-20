From python:3.11-slim

Run apt-get update && apt-get install -y \ ffmpeg \ portaudio19-dev \ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]
