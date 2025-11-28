-- Schema creation for Strategy Engine Pro
-- Enable extensions
create extension if not exists pgcrypto;

-- Tables
create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  username varchar(50) unique not null,
  email varchar(255) unique not null,
  password_hash varchar(255) not null,
  role varchar(20) default 'trader' check (role in ('admin','trader','viewer')),
  telegram_id varchar(50),
  api_keys jsonb default '{}'::jsonb,
  settings jsonb default '{"risk_tolerance":0.5,"max_daily_loss":1000,"default_position_size":100,"auto_trading_enabled":false}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.strategies (
  id uuid primary key default gen_random_uuid(),
  name varchar(100) not null,
  description text,
  type varchar(50) not null check (type in ('breakout','mean_reversion','momentum','sentiment','hybrid')),
  parameters jsonb default '{}'::jsonb,
  performance_metrics jsonb default '{"total_trades":0,"win_rate":0,"avg_pnl":0,"max_drawdown":0,"sharpe_ratio":0}'::jsonb,
  is_active boolean default true,
  created_by uuid references public.users(id),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.trades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) not null,
  strategy_id uuid references public.strategies(id),
  symbol varchar(20) not null,
  side varchar(10) not null check (side in ('buy','sell')),
  entry_price numeric(20,8) not null,
  exit_price numeric(20,8),
  quantity numeric(20,8) not null,
  stop_loss numeric(20,8),
  take_profit numeric(20,8),
  status varchar(20) default 'open' check (status in ('open','closed','cancelled')),
  pnl numeric(20,8),
  fees numeric(20,8) default 0,
  execution_time timestamptz default now(),
  close_time timestamptz,
  broker varchar(20) not null,
  metadata jsonb default '{}'::jsonb
);
create index if not exists idx_trades_user_id on public.trades(user_id);
create index if not exists idx_trades_symbol on public.trades(symbol);
create index if not exists idx_trades_status on public.trades(status);

create table if not exists public.market_data (
  id uuid primary key default gen_random_uuid(),
  symbol varchar(20) not null,
  timestamp timestamptz not null,
  open numeric(20,8) not null,
  high numeric(20,8) not null,
  low numeric(20,8) not null,
  close numeric(20,8) not null,
  volume numeric(20,8) not null,
  source varchar(20) not null
);
create index if not exists idx_market_data_symbol_timestamp on public.market_data(symbol, timestamp);
create unique index if not exists unique_market_data on public.market_data(symbol, timestamp, source);

create table if not exists public.sentiment_data (
  id uuid primary key default gen_random_uuid(),
  symbol varchar(20) not null,
  timestamp timestamptz default now(),
  source varchar(20) not null check (source in ('twitter','reddit','news')),
  sentiment_score numeric(3,2) not null check (sentiment_score between -1 and 1),
  confidence numeric(3,2) not null check (confidence between 0 and 1),
  text_sample text,
  metadata jsonb default '{}'::jsonb
);
create index if not exists idx_sentiment_symbol_timestamp on public.sentiment_data(symbol, timestamp);

-- updated_at trigger
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists update_users_updated_at on public.users;
create trigger update_users_updated_at before update on public.users for each row execute function public.update_updated_at_column();

drop trigger if exists update_strategies_updated_at on public.strategies;
create trigger update_strategies_updated_at before update on public.strategies for each row execute function public.update_updated_at_column();
