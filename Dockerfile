FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Hugging face spaces usually map to port 7860
EXPOSE 7860

# Run the gunicorn server with our app
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
