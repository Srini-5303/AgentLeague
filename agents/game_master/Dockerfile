# GM orchestrator image — deployed to Azure Container Apps (NOT Static Web Apps,
# which cannot stream SSE). Build for linux/amd64.
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt requirements-azure.txt ./
RUN pip install --no-cache-dir -r requirements-azure.txt

# Copy the application (orchestrator, shared seam, agent prompts, knowledge).
COPY shared/ ./shared/
COPY agents/ ./agents/
COPY knowledge/ ./knowledge/

ENV RUNTIME=azure
EXPOSE 8000

# Single worker keeps the per-session in-process lock authoritative. Scale out via
# Container Apps replicas only once session affinity / distributed locks are added.
CMD ["uvicorn", "agents.game_master.app:app", "--host", "0.0.0.0", "--port", "8000"]
