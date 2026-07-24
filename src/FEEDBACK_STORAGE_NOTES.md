# Feedback storage and access

## Where submissions go

The floating feedback form sends:

```text
POST /api/feedback
```

The backend appends one JSON object per line to:

```text
${APP_DATA_DIR}/feedback.jsonl
```

When `APP_DATA_DIR` is unset, the path is:

```text
/tmp/actigraphy-ui-data/feedback.jsonl
```

`/tmp` is container-local and normally disappears when the instance is replaced. For OBI/Azure, mount a persistent Azure Files volume and set `APP_DATA_DIR` to that mount, for example:

```text
APP_DATA_DIR=/data/actigraphy-ui
```

The backend, not Vercel, stores the report. The storage location therefore follows the backend selected by `VITE_API_BASE_URL`.

## Information stored with each report

The form does not upload raw actigraphy data. It stores the user's message plus diagnostic context:

- feedback ID and UTC submission time;
- category and optional contact email;
- current workflow step and client URL;
- selected file names, extensions, sizes, and analysis selection state;
- current endpoint, request ID, job/progress state, and visible errors;
- activity mapping, analysis mode/scope, selected families/metrics, sleep settings, preprocessing settings, analysis windows, and light selections;
- frontend version, backend URL, browser information, and client timestamp.

## Review in the application

After `FEEDBACK_ADMIN_TOKEN` is configured on the backend, open:

```text
https://YOUR-FRONTEND/?feedback-admin=1
```

Enter the administrator token to search reports, inspect the complete stored context, and download CSV or JSONL exports. The token is retained only in browser session storage for the current tab.

## Protected API access

Set a long random backend secret:

```text
FEEDBACK_ADMIN_TOKEN=replace-with-a-long-random-secret
```

Then list recent reports:

```bash
curl -H "X-Feedback-Admin-Token: $FEEDBACK_ADMIN_TOKEN" \
  "https://YOUR-BACKEND/api/admin/feedback?limit=100"
```

Optional filters:

```text
/api/admin/feedback?category=issue&search=gt3x&limit=250
```

Download CSV:

```bash
curl -L -H "Authorization: Bearer $FEEDBACK_ADMIN_TOKEN" \
  "https://YOUR-BACKEND/api/admin/feedback/export?format=csv" \
  -o feedback.csv
```

Download JSONL by changing `format=jsonl`.

The list/export endpoints return `503` until `FEEDBACK_ADMIN_TOKEN` is configured and `401` for an incorrect token.

## Local/container export

From the source directory:

```bash
python -m backend.export_feedback \
  --format csv \
  --output feedback.csv
```

Specify `--input /mounted/path/feedback.jsonl` when exporting a copied or mounted feedback file.
