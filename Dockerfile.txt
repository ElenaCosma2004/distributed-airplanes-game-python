FROM python:3.12-slim

WORKDIR /app

COPY server.py /app/server.py
COPY configs /app/configs

EXPOSE 8708

CMD ["python3", "server.py"]