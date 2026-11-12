FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 10001 app && adduser --system --uid 10001 --ingroup app app

COPY pyproject.toml README.md ./
COPY offerbot ./offerbot
COPY "bot3 (1).py" ./

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN mkdir -p /app/data && chown -R app:app /app

USER app

CMD ["python", "bot3 (1).py"]
