# Building wheel for python env
tinyfaas doesn't have build tools for python, so we need to build the wheel in a separate environment.  
There is a problem with alpine+librdkafka which installs an obsolete librdkafka and confluent_kafka will complain about it. Check [this gist](https://gist.github.com/jaihind213/e82d41dc79f52cfa64ca32350bdb27df) for workaround.


Build the Docker image:
```bash
docker build -t my-python-alpine .
```

Run the Docker container:
```bash
docker run --name my-python-alpine-container -it my-python-alpine bash
```

Copy the grpcio wheel file out of the Docker container (the wheel's file name may be different):
```bash
docker cp my-python-alpine-container:/app/grpcio-1.64.1-cp311-cp311-linux_aarch64.whl .
```

Copy the confluent_kafka wheel file out of the Docker container:
```bash
docker cp my-python-alpine-container:/app/confluent_kafka-<version>-cp<python-version>-cp<python-version>m-manylinux2010_x86_64.whl .
```
Replace <version> and <python-version> with the actual version number and Python version in the filename.