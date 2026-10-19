FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# baixa o modelo de transcricao (Whisper small, ~500 MB) no build, pra nao
# depender de internet nem demorar na primeira transcricao depois de subir
RUN python -c "from faster_whisper import download_model; download_model('small')"

# mensagens do print (jobs de audio, alertas) aparecem na hora no docker compose logs
ENV PYTHONUNBUFFERED=1

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
