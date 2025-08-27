FROM python:3.11-slim

# Copy requirements first to leverage Docker cache
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set Django environment variables.  Feel free to override these in your
# own environment or remove them to use your own management script.  The
# default settings point to the included settings module.
ENV DJANGO_SETTINGS_MODULE=athena_drf.settings
ENV PYTHONUNBUFFERED=1

# Expose the default Django runserver port
EXPOSE 8000

# Entrypoint is set in docker-compose.yml; see that file for run commands.