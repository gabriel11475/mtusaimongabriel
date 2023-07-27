# Use uma imagem base do RabbitMQ disponível no Docker Hub
FROM rabbitmq:3.8.17-management

# Use the official Python base image with the desired version
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --ignore-installed uvicorn==0.23.1
RUN pip install postgres
RUN pip install rabbitmq
RUN pip install pika
# Copy the source code into the container
COPY . .
# Expose the port that the FastAPI app will listen on
EXPOSE 8000
EXPOSE 5672
EXPOSE 15672
RUN echo "funfou"
CMD ["sh", "-c", "rabbitmq-server start & python main.py"]
