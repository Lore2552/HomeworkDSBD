FROM python:3.9-slim

WORKDIR /app

COPY data-collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data-collector/ .
COPY protos/ ./protos/

RUN python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/user_manager.proto

CMD ["sh", "-c", "python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/user_manager.proto && python data-collector.py"]
