# Dockerfile para WhatsApp MCP Secure
FROM golang:1.21-alpine AS go-builder

WORKDIR /app
COPY whatsapp-bridge/ ./whatsapp-bridge/
WORKDIR /app/whatsapp-bridge

RUN apk add --no-cache gcc musl-dev sqlite-dev
RUN go mod download
RUN CGO_ENABLED=1 go build -o whatsapp-bridge main.go handlers.go utils.go

FROM python:3.11-alpine AS python-builder

WORKDIR /app
COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM alpine:latest

# Instalar dependencias del sistema
RUN apk add --no-cache \
    sqlite \
    sqlcipher \
    python3 \
    py3-pip \
    ca-certificates \
    tzdata

# Crear usuario no privilegiado
RUN addgroup -g 1001 whatsapp && \
    adduser -D -s /bin/sh -u 1001 -G whatsapp whatsapp

# Crear directorios
RUN mkdir -p /app/{data,auth,logs,backups} && \
    chown -R whatsapp:whatsapp /app

# Copiar binarios
COPY --from=go-builder /app/whatsapp-bridge/whatsapp-bridge /app/
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY mcp-server/ /app/mcp-server/
COPY scripts/ /app/scripts/
COPY .env.example /app/.env

# Configurar permisos
RUN chown -R whatsapp:whatsapp /app && \
    chmod +x /app/whatsapp-bridge && \
    chmod +x /app/scripts/*.py

USER whatsapp
WORKDIR /app

# Configurar variables de entorno
ENV PYTHONPATH=/app/mcp-server
ENV TZ=UTC

# Exponer puertos
EXPOSE 8080 8081

# Script de inicio
COPY --chown=whatsapp:whatsapp <<EOF /app/start.sh
#!/bin/sh
set -e

echo "Iniciando WhatsApp MCP Secure..."

# Verificar configuración
if [ ! -f ".env" ]; then
    echo "Error: archivo .env no encontrado"
    exit 1
fi

# Iniciar WhatsApp Bridge en background
echo "Iniciando WhatsApp Bridge..."
./whatsapp-bridge &
BRIDGE_PID=$!

# Esperar que el bridge esté listo
sleep 5

# Iniciar MCP Server
echo "Iniciando MCP Server..."
cd mcp-server
python main.py &
MCP_PID=$!

# Función para manejar señales
cleanup() {
    echo "Cerrando servicios..."
    kill $BRIDGE_PID $MCP_PID 2>/dev/null || true
    wait
    exit 0
}

trap cleanup TERM INT

# Esperar a que terminen los procesos
wait $BRIDGE_PID $MCP_PID
EOF

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
