FROM python:3.12-slim
WORKDIR /srv
COPY engine/requirements.txt engine/requirements.txt
# Devanagari fonts for the shareable panchang image card (Pillow + raqm shaping)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-core fonts-freefont-ttf && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r engine/requirements.txt
COPY engine engine
COPY data data
COPY web web
# Service-worker cache version = the git commit, so every deploy refreshes the offline app shell
ARG GIT_SHA=dev
RUN sed -i "s/kundali-v1/kundali-${GIT_SHA}/" /srv/web/sw.js && sed -i "s#assets/app\.\(css\|js\)\"#assets/app.\1?v=${GIT_SHA}\"#g" /srv/web/index.html
ENV KUNDALI_EPHEMERIS_DIR=/srv/ephemeris KUNDALI_BACKEND=jpl
# fetch NASA JPL DE440s (~32 MB) at build time so the container starts offline
RUN mkdir -p /srv/ephemeris && cd /srv/engine && python -c "from jyotish.ephemeris import JPLBackend; JPLBackend()"
WORKDIR /srv/engine
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]