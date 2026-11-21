FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY silicon_teahouse ./silicon_teahouse

RUN pip install --no-cache-dir .

CMD ["silicon-teahouse"]
