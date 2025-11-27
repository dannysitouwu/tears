FROM python:3.11-slim
WORKDIR /app
COPY . /app/
COPY ./requirements.txt ./requirements.txt
# COPY generator.py /app/
RUN python3 -m pip install --no-cache-dir -r ./requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]