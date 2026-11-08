FROM python:3.12-slim
WORKDIR /srv
COPY engine/requirements.txt engine/requirements.txt
RUN pip install --no-cache-dir -r engine/requirements.txt
COPY engine engine
COPY data data
ENV KUNDALI_EPHEMERIS_DIR=/srv/ephemeris KUNDALI_BACKEND=jpl
# fetch NASA JPL DE440s (~32 MB) at build time so the container starts offline
RUN mkdir -p /srv/ephemeris && cd /srv/engine && python -c "from jyotish.ephemeris import JPLBackend; JPLBackend()"
WORKDIR /srv/engine
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
