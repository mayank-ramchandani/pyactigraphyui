-- Supabase tables for Google login + saved run history.
-- Run this in Supabase SQL Editor after creating your project and enabling Google as an auth provider.

create extension if not exists pgcrypto;

create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  user_email text,
  original_filename text,
  file_type text,
  file_size_mb numeric,
  status text not null default 'completed',
  analysis_mode text,
  selected_algorithm text,
  activity_channel text,
  activity_mapping text not null default 'original',
  detected_input_type text,
  results jsonb not null default '{}'::jsonb,
  qc_warnings jsonb not null default '[]'::jsonb,
  support_file_summary jsonb,
  analysis_config jsonb,
  error_message text,
  app_version text,
  created_at timestamptz not null default now()
);

-- Safe migration for projects where analysis_runs already existed before activity mapping was added.
alter table public.analysis_runs
  add column if not exists activity_mapping text not null default 'original';

alter table public.analysis_runs enable row level security;

drop policy if exists "Users can read their own analysis runs" on public.analysis_runs;
create policy "Users can read their own analysis runs"
  on public.analysis_runs
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert their own analysis runs" on public.analysis_runs;
create policy "Users can insert their own analysis runs"
  on public.analysis_runs
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own analysis runs" on public.analysis_runs;
create policy "Users can delete their own analysis runs"
  on public.analysis_runs
  for delete
  using (auth.uid() = user_id);

create index if not exists analysis_runs_user_created_idx
  on public.analysis_runs (user_id, created_at desc);
