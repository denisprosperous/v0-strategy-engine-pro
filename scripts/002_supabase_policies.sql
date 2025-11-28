-- Enable RLS
alter table public.users enable row level security;
alter table public.strategies enable row level security;
alter table public.trades enable row level security;
alter table public.market_data enable row level security;
alter table public.sentiment_data enable row level security;

-- Authenticated users may read their own user row
create policy if not exists users_select_self on public.users
  for select using (auth.uid() = id);

-- Users may update their own row (e.g., settings)
create policy if not exists users_update_self on public.users
  for update using (auth.uid() = id);

-- Strategies: public read of active strategies; owner write
create policy if not exists strategies_select_active on public.strategies
  for select using (is_active = true);

create policy if not exists strategies_owner_modify on public.strategies
  for all using (created_by = auth.uid());

-- Trades: owner read/write
create policy if not exists trades_owner_select on public.trades
  for select using (user_id = auth.uid());

create policy if not exists trades_owner_insert on public.trades
  for insert with check (user_id = auth.uid());

create policy if not exists trades_owner_update on public.trades
  for update using (user_id = auth.uid());

-- Market data & sentiment: read-only to all authenticated
create policy if not exists market_data_read on public.market_data
  for select using (true);

create policy if not exists sentiment_data_read on public.sentiment_data
  for select using (true);
