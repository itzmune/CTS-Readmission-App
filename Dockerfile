
FROM python:3.11-slim
# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2 and mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (but NOT .env)
COPY . .

# Expose port for Cloud Run
EXPOSE 8080

# Run the app with Gunicorn (better for production than flask run)
# Gunicorn will serve app:app (module:object)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
# Copy everything
COPY . .

# Ensure CSV file goes inside /app/
# If you want the CSV inside container root
COPY routes/readmission_data_export.csv /app/routes/readmission_data_export.csv




