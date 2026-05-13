FROM python:3.11-slim

# Instalar dependências do sistema (OBRIGATÓRIO para geopandas)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Variáveis de ambiente
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Diretório de trabalho
WORKDIR /app

# Copiar arquivos
COPY . .

# Instalar dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Porta obrigatória do Cloud Run
EXPOSE 8080

# Rodar Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
