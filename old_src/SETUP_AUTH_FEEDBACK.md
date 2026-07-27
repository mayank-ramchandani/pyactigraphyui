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

## Feedback storage and administration

Feedback is stored in `${APP_DATA_DIR}/feedback.jsonl`. Use persistent mounted storage in OBI/Azure, set `FEEDBACK_ADMIN_TOKEN`, and use the protected `/api/admin/feedback` and `/api/admin/feedback/export` endpoints. The report includes selected settings, filenames, progress, request ID, current errors, deployment URLs, and browser context, but not raw uploaded files. See [FEEDBACK_STORAGE_NOTES.md](FEEDBACK_STORAGE_NOTES.md) for commands and deployment details.
