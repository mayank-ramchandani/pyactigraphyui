# Feedback, optional Google login, and saved run history setup

The current public workflow does not require login and does not place Supabase setup instructions on page 1. Authentication and saved runs remain optional deployment features controlled separately from the ten-page analysis workflow.

This source includes two new features:

1. A feedback button that posts issue reports to the backend endpoint `/api/feedback`.
2. Optional Google login and saved previous runs using Supabase Auth + Supabase Postgres.

## Frontend dependency

Install the Supabase browser client in the React/Vite project:

```bash
npm install @supabase/supabase-js
```

## Supabase setup for Google login and saved runs

1. Create a Supabase project.
2. In Supabase, enable Google as an Auth provider.
3. Add the deployed frontend URL to Supabase Auth redirect URLs.
4. Run `src/supabase_schema.sql` in the Supabase SQL Editor.
5. Add these frontend environment variables:

```bash
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_PUBLIC_KEY
```

The app stores analysis results and metadata only. It does not store raw uploaded actigraphy files by default.

## Feedback storage

The backend writes feedback as newline-delimited JSON to:

```bash
APP_DATA_DIR/feedback.jsonl
```

Set `APP_DATA_DIR` to a persistent mounted folder on OBI Cloud if you want feedback to survive container restarts.

Example:

```bash
APP_DATA_DIR=/data/actigraphy-ui
```

If you do not set `APP_DATA_DIR`, the backend uses `/tmp/actigraphy-ui-data`, which is useful for testing but not durable on most hosted containers.
