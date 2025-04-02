FROM python:3.13

WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY . /app
COPY requirements.txt .
RUN pip install standard-imghdr
RUN pip install update
RUN pip install -r requirements.txt

COPY . .
ENV ACCESS_TOKEN = 7640799016:AAFzI-9-iuHa2-kc81xwlK_HMIk6UYiOoXk
ENV BASICURL = https://genai.hkbu.edu.hk/general/rest
ENV MODELNAME = gpt-4-o-mini
ENV APIVERSION = 2024-05-01-preview
ENV ACCESS_TOKEN = 9c65fb74-8056-4df1-85f3-9f7da684db3f
CMD ["python", "chatbot.py"]