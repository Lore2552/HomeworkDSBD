FROM python:3.9-slim

WORKDIR /app

COPY user-manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY user-manager/ .
COPY protos/ ./protos/

RUN python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/user_manager.proto

CMD ["sh", "-c", "python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/user_manager.proto && python user-manager.py"]
