FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade --no-cache-dir pip && pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
