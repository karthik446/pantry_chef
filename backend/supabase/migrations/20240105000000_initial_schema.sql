-- supabase/migrations/20240105000000_initial_schema.sql

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Create and setup auth schema
create schema if not exists auth;
grant usage on schema auth to service_role;
grant all on all tables in schema auth to service_role;
grant all on all sequences in schema auth to service_role;

-- Create role enum
CREATE TYPE user_role AS ENUM ('user', 'admin');

-- Create tables
create table public.users (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  created_at timestamptz default now(),
  is_active boolean default true,
  raw_user_meta_data jsonb,
  role user_role NOT NULL DEFAULT 'user'
);

-- User preferences with RLS policies
create table public.user_preferences (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  spice_level int check (spice_level between 1 and 5),
  unique(user_id)
);

create table public.categories (
  id uuid primary key default uuid_generate_v4(),
  name text unique not null,
  created_at timestamptz default now()
);

create table public.ingredients (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  category_id uuid references categories(id) on delete set null,
  created_at timestamptz default now()
);

create table public.pantry_items (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  ingredient_id uuid references ingredients(id) on delete cascade,
  quantity decimal,
  unit text,
  expiry_date timestamptz,
  created_at timestamptz default now()
);

create table public.recipes (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  instructions text not null,
  prep_time int,
  cook_time int,
  total_time int,
  servings int,
  source_url text,
  created_from_search_query text,
  created_at timestamptz default now()
);

create table public.recipe_ingredients (
  recipe_id uuid references recipes(id) on delete cascade,
  ingredient_id uuid references ingredients(id) on delete cascade,
  quantity decimal,
  unit text,
  primary key (recipe_id, ingredient_id)
);

create table public.user_favorites (
  user_id uuid references users(id) on delete cascade,
  recipe_id uuid references recipes(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, recipe_id)
);

-- RLS Policies
alter table public.users enable row level security;
alter table public.user_preferences enable row level security;
alter table public.pantry_items enable row level security;
alter table public.user_favorites enable row level security;

-- User policies
DROP POLICY IF EXISTS "Users can view own data" ON public.users;
CREATE POLICY "Users can view own data"
  ON public.users FOR SELECT
  USING (
    auth.uid() = id OR 
    auth.jwt() ->> 'role' = 'service_role'
  );

-- User preferences policies
DROP POLICY IF EXISTS "Users can manage own preferences" ON public.user_preferences;
CREATE POLICY "Users can manage own preferences or admins can manage all"
  ON public.user_preferences FOR ALL
  USING (auth.uid() = user_id OR EXISTS (
    SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
  ))
  WITH CHECK (auth.uid() = user_id OR EXISTS (
    SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
  ));

-- Pantry items policies
DROP POLICY IF EXISTS "Users can manage own pantry" ON public.pantry_items;
CREATE POLICY "Users can manage own pantry or admins can manage all"
  ON public.pantry_items FOR ALL
  USING (auth.uid() = user_id OR EXISTS (
    SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
  ))
  WITH CHECK (auth.uid() = user_id OR EXISTS (
    SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin'
  ));

-- Create admin user in auth.users first
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  gen_random_uuid(),
  'authenticated',
  'authenticated',
  'admin@example.com',
  crypt('admin123', gen_salt('bf')),
  now(),
  now(),
  now()
);

-- Then link the admin user to public.users
DO $$
DECLARE
  auth_user_id uuid;
BEGIN
  SELECT id INTO auth_user_id FROM auth.users WHERE email = 'admin@example.com';
  
  INSERT INTO public.users (id, email, role)
  VALUES (auth_user_id, 'admin@example.com', 'admin');
END $$;

-- Add after creating users table
CREATE OR REPLACE FUNCTION public.get_user_role(user_id uuid)
RETURNS text
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT role::text
  FROM users
  WHERE id = user_id;
$$;    