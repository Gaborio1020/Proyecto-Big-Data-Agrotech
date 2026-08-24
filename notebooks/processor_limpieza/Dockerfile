FROM python:3.10-slim

WORKDIR /app

# Copiamos el archivo de dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el script principal del processor
COPY processor.py .

# Comando por defecto al iniciar el contenedor
CMD ["python", "processor.py"]
