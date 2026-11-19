FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt requirements.lock.txt ./
RUN pip install -r requirements.lock.txt && useradd --create-home --uid 10001 app && mkdir /data && chown app:app /data
COPY --chown=app:app app ./app
COPY --chown=app:app frontend ./frontend
COPY --chown=app:app tests ./tests
COPY --chown=app:app loadtest ./loadtest
COPY --chown=app:app deploy/elasticity ./deploy/elasticity
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
