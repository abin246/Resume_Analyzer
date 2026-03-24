# Hyperstack LocalAI Deployment

1. Copy this folder to your Hyperstack VM.
2. Put model YAML and model files under `./models`.
3. Start service:

```bash
docker compose -f docker-compose.localai.yml up -d
```

4. Verify from VM:

```bash
curl http://127.0.0.1:8080/v1/models
```

5. Expose `8080` with your Hyperstack networking / reverse proxy and TLS.
6. In Render backend env set:

- `LOCALAI_BASE_URL=https://<your-hyperstack-localai-domain>/v1`
