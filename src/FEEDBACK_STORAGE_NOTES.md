# Feedback storage notes

The feedback form posts to the FastAPI backend endpoint:

```text
POST /api/feedback
```

The backend writes each feedback submission as one JSON line to:

```text
${APP_DATA_DIR}/feedback.jsonl
```

If `APP_DATA_DIR` is not set, the backend defaults to:

```text
/tmp/actigraphy-ui-data/feedback.jsonl
```

That default is fine for local testing, but it is not durable on most hosted deployments. In production, set `APP_DATA_DIR` to a persistent directory on the machine/container that runs the backend API.

Examples:

```bash
APP_DATA_DIR=/data/actigraphy-ui
```

or, if using Docker:

```bash
docker run \
  -e APP_DATA_DIR=/data/actigraphy-ui \
  -v /srv/actigraphy-ui-data:/data/actigraphy-ui \
  your-image-name
```

Where the file is stored depends on where the backend is deployed:

- If the backend API is running on OBI's backend server, the feedback file will be on OBI's backend server.
- If the backend API is running on Render, the feedback file will be on Render's filesystem. Use a Render persistent disk and point `APP_DATA_DIR` at that mounted disk path.
- If only the frontend is on Vercel, the feedback is not stored on Vercel; it is sent to whichever backend URL `VITE_API_BASE_URL` points to.
