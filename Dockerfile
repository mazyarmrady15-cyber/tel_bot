From debian:bookworm

Run apt-get update && apt-get install -y \ python3 \ python3-pip \ ffmpeg \ portaudio19-dev \ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]
