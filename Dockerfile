# Mini Healthcare Assistant — container image (optional; Streamlit-SDK
# Hugging Face Spaces don't require this, it's provided for portability /
# running the app outside HF, e.g. locally or on another host).

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Generate the synthetic dataset at build time so it's ready on first run
RUN python data/generate_data.py

EXPOSE 8501

# GROQ_API_KEY should be passed at runtime, e.g.:
#   docker run -e GROQ_API_KEY=your_key -p 8501:8501 mini-healthcare-assistant
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
