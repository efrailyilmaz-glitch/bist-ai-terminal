# BIST AI Web Terminal

Standalone web application prepared for deployment.

## Local run
```bash
bash run.sh
```
Open http://localhost:8000

## Deployment
- Render reads `render.yaml`
- Railway can use `Dockerfile` or `Procfile`
- Health endpoint: `/health`

The current packaged market dataset is DEMO/CACHE. Live broker execution is disabled.
