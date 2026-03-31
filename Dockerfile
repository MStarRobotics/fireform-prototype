FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python -m pip install --no-cache-dir -e .

CMD ["python", "-m", "fireform.cli", "--text", "Engine 1 responded to a structure fire at 12 Main St, Springfield, NY at 01:15 on 2026-03-31."]
