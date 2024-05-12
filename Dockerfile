# Using the latest Python 3 slim image
FROM python:3.12-slim

# Install pymongo for MongoDB integration
RUN pip install pymongo

# Setting up the working directory
WORKDIR /app

# Copying the necessary files
COPY . /app

# Exposing the HTTP and Socket server ports
EXPOSE 3001 5001

# Command to run the application
CMD ["python", "main.py"]
