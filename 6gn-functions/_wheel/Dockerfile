FROM python:3.11-alpine

# Install dependencies
RUN apk add --no-cache \
    gcc \
    g++ \
    make \
    linux-headers \
    libc-dev \
    python3-dev \
    musl-dev \
    openssl-dev \
    bash \
    curl \
    tar
#    librdkafka-dev

# Set working directory
WORKDIR /app

 #2.4.0 was used last time
ENV LIBRD_VER=2.5.0

# https://gist.github.com/jaihind213/e82d41dc79f52cfa64ca32350bdb27df
RUN apk add --no-cache --virtual .make-deps wget git  && apk add --no-cache musl-dev zlib-dev openssl zstd-dev pkgconfig libc-dev
#RUN wget https://github.com/edenhill/librdkafka/archive/v${LIBRD_VER}.tar.gz
RUN wget https://github.com/confluentinc/librdkafka/archive/v${LIBRD_VER}.tar.gz
RUN tar -xvf v${LIBRD_VER}.tar.gz && cd librdkafka-${LIBRD_VER} && ./configure --prefix /usr && make && make install

# Download, extract, build, and install librdkafka from source (OBSELETE, librdkafka > 2.4.0 is needed)
#RUN curl -L http://mirrordirector.raspbian.org/raspbian/pool/main/libr/librdkafka/librdkafka_1.6.0.orig.tar.gz -o librdkafka.tar.gz && \
#    tar -xzf librdkafka.tar.gz && \
#    cd librdkafka-1.6.0 && \
#    ./configure && \
#    make && \
#    make install && \
#    ldconfig && \
#    cd .. && \
#    rm -rf librdkafka.tar.gz librdkafka-1.6.0


# Copy the requirements file
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Build the confluent_kafka wheel
RUN pip wheel --no-binary :all: confluent_kafka

# Build the grpcio wheel
RUN pip wheel --no-binary :all: grpcio