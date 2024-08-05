FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install pdm && pdm install --prod
CMD ["pdm", "run", "python", "main.py"]
