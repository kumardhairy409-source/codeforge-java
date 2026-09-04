FROM eclipse-temurin:21-jdk

WORKDIR /runner

COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir -r requirements.txt

COPY runner.py .

RUN useradd -m runner

USER runner

EXPOSE 8000

CMD ["python3", "runner.py"]
