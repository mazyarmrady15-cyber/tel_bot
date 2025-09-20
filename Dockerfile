# استفاده از پایتون سبک
FROM python:3.11-slim

# نصب ابزارهای لازم برای دانلود و استخراج
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# مسیر کاری
WORKDIR /app

# دانلود ffmpeg استاتیک و کپی به /usr/local/bin
RUN wget -qO /tmp/ffmpeg.tar.xz "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
 && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
 && cp /tmp/ffmpeg-*-static/ffmpeg /usr/local/bin/ \
 && cp /tmp/ffmpeg-*-static/ffprobe /usr/local/bin/ \
 && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
 && rm -rf /tmp/ffmpeg*

# کپی کردن کل پروژه
COPY . .

# نصب کتابخانه‌های پایتونی
RUN pip install --no-cache-dir -r requirements.txt

# اجرای ربات
CMD ["python", "bot.py"]
