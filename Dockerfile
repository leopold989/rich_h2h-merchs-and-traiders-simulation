FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY config ./config
COPY schemas ./schemas
COPY fixtures ./fixtures
COPY docs ./docs
COPY examples ./examples
COPY scripts ./scripts

EXPOSE 8099

CMD ["rich-h2h-simulator"]
