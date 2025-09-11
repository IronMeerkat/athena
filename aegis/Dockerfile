FROM athena-infrastructure-base:latest

# Install geospatial system libraries required by GeoDjango (GEOS/PROJ/GDAL)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       gdal-bin libgdal-dev proj-bin proj-data libproj-dev libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Entrypoints
RUN chmod +x scripts/entrypoint_web.sh scripts/entrypoint_worker.sh

# Set Django environment variables.  Feel free to override these in your
# own environment or remove them to use your own management script.  The
# default settings point to the included settings module.
ENV DJANGO_SETTINGS_MODULE=aegis.settings
ENV PYTHONUNBUFFERED=1

# Expose the default Django runserver port
EXPOSE 8000

# Entrypoint is set in docker-compose.yml; see that file for run commands.