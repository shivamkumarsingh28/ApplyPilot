FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY applypilot_bot ./applypilot_bot
RUN useradd -m bot && mkdir -p /srv/data && chown -R bot /srv
USER bot
CMD ["python", "-m", "applypilot_bot.main"]
