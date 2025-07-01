FROM python:3.13.2

RUN pip install --upgrade pip

# Install build dependencies
RUN apt update -y && apt install -y python3-dev libsecp256k1-dev

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock main.py ./
COPY vrf_worker ./vrf_worker/

CMD ["uv", "run", "main.py"]
