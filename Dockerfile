FROM python:3.13.5-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    python3-pkg-resources \
    && rm -rf /var/lib/apt/lists/*

# ENV SECRET_KEY='9fcf5d77-cd18-4109-a6f7-37e8b218233c'
# ENV MAX_CONTENT_LENGTH = 1024 * 1024
# ENV UPLOAD_FOLDER = 'uploads'

# Create app directory
WORKDIR /app

# Install app dependencies
COPY requirements.txt /app

RUN pip3 install --upgrade pip setuptools

RUN pip3 install --no-cache-dir -r requirements.txt --verbose

# Bundle app source
COPY . .

EXPOSE 5000
CMD [ "flask", "run","--host","0.0.0.0","--port","5000"]