FROM python:3.12-slim


# Prevent Python cache files and show logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000


# Set the container working directory.
WORKDIR /app


# Install the API dependencies.
COPY requirements-api.txt .

RUN python -m pip install \
    --no-cache-dir \
    --upgrade pip \
    && python -m pip install \
    --no-cache-dir \
    -r requirements-api.txt


# Copy the FastAPI source code.
COPY api ./api


# Copy the trained eight-week forecasting models.
COPY models/schedule_informed_rf_8week.joblib ./models/schedule_informed_rf_8week.joblib


# Copy the model feature definitions.
COPY models/schedule_informed_rf_features.joblib ./models/schedule_informed_rf_features.joblib


# Copy only the dataset required by the API.
COPY data/processed/cement_operations_merged.csv ./data/processed/cement_operations_merged.csv


# Expose the FastAPI port.
EXPOSE 8000


# Allow extra startup time for the 892 MB model.
HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=90s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"


# Use one worker so that the large model is loaded only once.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]