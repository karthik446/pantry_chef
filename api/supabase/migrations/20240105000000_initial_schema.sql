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

create table public.ingredients (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
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
  id uuid primary key default uuid_generate_v4(),
  recipe_id uuid references recipes(id) on delete cascade,
  ingredient_id uuid references ingredients(id) on delete cascade,
  quantity decimal,
  unit text
);

create table public.user_favorites (
  user_id uuid references users(id) on delete cascade,
  recipe_id uuid references recipes(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, recipe_id)
);

-- Table to track user search history
create table public.user_search_history (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  search_query text not null,
  created_at timestamptz default now(),
  results_count int,
  selected_recipe_id uuid references recipes(id) on delete set null
);

-- Table to track which recipes users have viewed
create table public.user_recipe_views (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  recipe_id uuid references recipes(id) on delete cascade,
  source_url text,
  viewed_at timestamptz default now(),
  view_duration_seconds int,
  came_from_search_id uuid references user_search_history(id) on delete set null,
  unique(user_id, recipe_id)
);

-- RLS Policies
alter table public.users enable row level security;
alter table public.user_preferences enable row level security;
alter table public.pantry_items enable row level security;
alter table public.user_favorites enable row level security;
alter table public.user_search_history enable row level security;
alter table public.user_recipe_views enable row level security;

-- User policies
DROP POLICY IF EXISTS "Users can view own data" ON public.users;
CREATE POLICY "Users can view own data"
  ON public.users FOR SELECT
  USING (
    auth.uid() = id OR 
    auth.jwt() ->> 'role' = 'service_role'
  );

-- Allow inserting users with matching auth ID
DROP POLICY IF EXISTS "Users can insert own data" ON public.users;
CREATE POLICY "Users can insert own data"
  ON public.users FOR INSERT
  WITH CHECK (
    auth.uid() = id OR 
    auth.jwt() ->> 'role' = 'service_role' OR
    current_setting('app.bypass_rls', true) = 'on'
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

-- User search history policies
DROP POLICY IF EXISTS "Users can view own search history" ON public.user_search_history;
CREATE POLICY "Users can view own search history"
  ON public.user_search_history FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can add own search history" ON public.user_search_history;
CREATE POLICY "Users can add own search history"
  ON public.user_search_history FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Recipe views policies
DROP POLICY IF EXISTS "Users can view own recipe views" ON public.user_recipe_views;
CREATE POLICY "Users can view own recipe views"
  ON public.user_recipe_views FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can add own recipe views" ON public.user_recipe_views;
CREATE POLICY "Users can add own recipe views"
  ON public.user_recipe_views FOR INSERT
  WITH CHECK (auth.uid() = user_id);

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

-- Create a materialized view for recipe-pantry matching
CREATE MATERIALIZED VIEW recipe_pantry_matches
WITH (fillfactor = 90) AS  -- Add fillfactor for better concurrent refresh performance
WITH recipe_ingredient_counts AS (
  SELECT recipe_id, COUNT(*) as total_ingredients
  FROM recipe_ingredients
  GROUP BY recipe_id
)
SELECT 
  r.id as recipe_id,
  r.title,
  u.id as user_id,
  COUNT(DISTINCT CASE WHEN pi.ingredient_id IS NOT NULL THEN ri.ingredient_id END) as matching_ingredients,
  ric.total_ingredients,
  (COUNT(DISTINCT CASE WHEN pi.ingredient_id IS NOT NULL THEN ri.ingredient_id END)::float / 
   NULLIF(ric.total_ingredients, 0) * 100) as match_percentage,
  array_agg(DISTINCT CASE WHEN pi.ingredient_id IS NOT NULL 
    THEN ri.ingredient_id END) FILTER (WHERE pi.ingredient_id IS NOT NULL) as matching_ingredient_ids,
  array_agg(DISTINCT CASE WHEN pi.ingredient_id IS NULL 
    THEN ri.ingredient_id END) FILTER (WHERE pi.ingredient_id IS NULL) as missing_ingredient_ids
FROM recipes r
CROSS JOIN users u
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN recipe_ingredient_counts ric ON ric.recipe_id = r.id
LEFT JOIN pantry_items pi ON pi.ingredient_id = ri.ingredient_id AND pi.user_id = u.id
GROUP BY r.id, r.title, u.id, ric.total_ingredients;

-- Create unique index to support concurrent refresh
CREATE UNIQUE INDEX idx_recipe_pantry_matches_unique 
ON recipe_pantry_matches(recipe_id, user_id);

-- Create index for better performance
CREATE INDEX idx_recipe_pantry_matches_user 
ON recipe_pantry_matches(user_id, match_percentage DESC);

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_recipe_pantry_matches()
RETURNS trigger AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY recipe_pantry_matches;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create triggers to refresh the materialized view
CREATE TRIGGER refresh_matches_pantry
  AFTER INSERT OR UPDATE OR DELETE ON pantry_items
  FOR EACH STATEMENT
  EXECUTE FUNCTION refresh_recipe_pantry_matches();

CREATE TRIGGER refresh_matches_recipe
  AFTER INSERT OR UPDATE OR DELETE ON recipe_ingredients
  FOR EACH STATEMENT
  EXECUTE FUNCTION refresh_recipe_pantry_matches();

CREATE TRIGGER refresh_matches_recipes
  AFTER INSERT OR UPDATE OR DELETE ON recipes
  FOR EACH STATEMENT
  EXECUTE FUNCTION refresh_recipe_pantry_matches();

CREATE OR REPLACE FUNCTION calculate_pantry_match(p_user_id UUID)
RETURNS TABLE (
  recipe_id UUID,
  title TEXT,
  match_percentage FLOAT,
  matching_ingredients INT,
  total_ingredients INT
) AS $$
BEGIN
  RETURN QUERY
  WITH recipe_ingredient_counts AS (
    SELECT recipe_id, COUNT(*) as total_ingredients
    FROM recipe_ingredients
    GROUP BY recipe_id
  )
  SELECT 
    r.id,
    r.title,
    (COUNT(DISTINCT ri.ingredient_id)::float / ric.total_ingredients * 100) as match_percentage,
    COUNT(DISTINCT ri.ingredient_id)::int as matching_ingredients,
    ric.total_ingredients
  FROM recipes r
  JOIN recipe_ingredients ri ON ri.recipe_id = r.id
  JOIN recipe_ingredient_counts ric ON ric.recipe_id = r.id
  WHERE ri.ingredient_id IN (
    SELECT ingredient_id 
    FROM pantry_items 
    WHERE user_id = p_user_id
  )
  GROUP BY r.id, r.title, ric.total_ingredients
  ORDER BY match_percentage DESC;
END;
$$ LANGUAGE plpgsql;

-- Helper function to get unseen recipes for a user
CREATE OR REPLACE FUNCTION get_unseen_recipes(p_user_id UUID, p_limit INT DEFAULT 10)
RETURNS TABLE (
  recipe_id UUID,
  title TEXT,
  source_url TEXT,
  match_percentage FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    rpm.recipe_id,
    rpm.title,
    r.source_url,
    rpm.match_percentage
  FROM recipe_pantry_matches rpm
  JOIN recipes r ON r.id = rpm.recipe_id
  WHERE rpm.user_id = p_user_id
  AND NOT EXISTS (
    SELECT 1 
    FROM user_recipe_views urv 
    WHERE urv.user_id = p_user_id 
    AND urv.recipe_id = rpm.recipe_id
  )
  ORDER BY rpm.match_percentage DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;    