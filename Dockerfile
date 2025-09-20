From python:3.11.6

Run apt-get update && apt-get install -y \ ffmpeg \ portaudio19-dev \ && rm -rf /var/lib/apt/lists/*

WORKIDR /app

COPY . .

RUN pip install --no-cache-dir -r
requirements.txt

CMD ["python", "bot.py"]
