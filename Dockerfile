FROM python:3.9-slim
WORKDIR /app

COPY . /app
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt 
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000
CMD ["flask", "run"]