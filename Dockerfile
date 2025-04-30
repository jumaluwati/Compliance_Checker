# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Install Streamlit and any other necessary packages
RUN pip install --no-cache-dir streamlit mysql-connector-python requests

# Copy the Streamlit app file into the container
COPY compliance.py .

# Expose the port Streamlit listens on
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "compliance.py"]