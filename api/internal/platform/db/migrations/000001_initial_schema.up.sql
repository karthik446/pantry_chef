-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create role enum
CREATE TYPE user_role AS ENUM ('user', 'admin');

-- Create measurement unit enum
CREATE TYPE measurement_unit AS ENUM (
    -- Volume
    'ml', 'l',                     -- metric
    'tsp', 'tbsp',                 -- teaspoon, tablespoon
    'fl_oz', 'cup', 'pint', 'qt', 'gal',  -- US volumes
    
    -- Weight
    'g', 'kg',                     -- metric
    'oz', 'lb',                    -- imperial/US
    
    -- Count
    'piece', 'pinch', 'handful',   -- countable/uncountable
    
    -- Other
    'to_taste',                    -- for seasonings
    'whole'                        -- for whole items
);

-- Create tables
CREATE TABLE public.users (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_number text UNIQUE NOT NULL CHECK (length(user_number) = 10 AND user_number ~ '^[0-9]+$'),
  password_hash text NOT NULL CHECK (length(password_hash) > 0),
  created_at TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_login_at TIMESTAMP(0) WITH TIME ZONE,
  is_active boolean NOT NULL DEFAULT true,
  role user_role NOT NULL DEFAULT 'user',
  password_changed_at TIMESTAMP(0) WITH TIME ZONE,
  failed_login_attempts int NOT NULL DEFAULT 0,
  locked_until TIMESTAMP(0) WITH TIME ZONE,
  CONSTRAINT valid_timestamps CHECK (
    (last_login_at IS NULL OR last_login_at >= created_at) AND
    (password_changed_at IS NULL OR password_changed_at >= created_at) AND
    (locked_until IS NULL OR locked_until >= created_at)
  )
);

CREATE TABLE public.user_preferences (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  preferences jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);






-- Add indexes for materialized view calculations


-- Add new table for refresh tokens after users table
CREATE TABLE public.refresh_tokens (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  expires_at TIMESTAMP(0) WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMP(0) WITH TIME ZONE,
  replaced_by_token text,
  user_agent text,
  client_ip text,
  CONSTRAINT valid_token_timestamps CHECK (
    expires_at > created_at AND
    (revoked_at IS NULL OR revoked_at >= created_at)
  )
);

-- Non User Tables

CREATE TABLE public.ingredients (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  normalized_name text,
  aliases text[] DEFAULT ARRAY[]::text[],
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE public.pantry_items (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ingredient_id uuid NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
  quantity decimal,
  unit measurement_unit,
  expiry_date timestamptz,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE public.recipes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  title text NOT NULL CHECK (length(trim(title)) > 0),
  instructions text NOT NULL CHECK (length(trim(instructions)) > 0),
  prep_time int NOT NULL CHECK (prep_time >= 0),
  cook_time int NOT NULL CHECK (cook_time >= 0),
  total_time int NOT NULL CHECK (total_time >= 0 AND total_time >= LEAST(prep_time, cook_time)),
  servings int CHECK (servings > 0),
  source_url text NOT NULL CHECK (source_url IS NULL OR source_url ~ '^https?://'),
  created_from_search_query text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE public.recipe_ingredients (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  recipe_id uuid REFERENCES recipes(id) ON DELETE CASCADE,
  ingredient_id uuid REFERENCES ingredients(id) ON DELETE CASCADE,
  quantity decimal,
  unit measurement_unit
--   CONSTRAINT valid_measurement CHECK (
--     (quantity IS NULL AND unit IS NULL) OR
--     (quantity IS NOT NULL AND unit IS NOT NULL)
--   )
);

CREATE TABLE public.user_favorites (
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  recipe_id uuid REFERENCES recipes(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (user_id, recipe_id)
);

CREATE TABLE public.user_recipe_interactions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  recipe_id uuid REFERENCES recipes(id) ON DELETE CASCADE,
  source_url text,
  interaction_type text NOT NULL CHECK (interaction_type IN ('view', 'from_search')),
  search_query text,
  created_at timestamptz DEFAULT now()
);



-- Create materialized view for recipe-pantry matching
CREATE MATERIALIZED VIEW recipe_pantry_matches AS
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

-- Create indexes
CREATE UNIQUE INDEX idx_recipe_pantry_matches_unique 
ON recipe_pantry_matches(recipe_id, user_id);

CREATE INDEX idx_recipe_pantry_matches_user 
ON recipe_pantry_matches(user_id, match_percentage DESC);

CREATE INDEX idx_pantry_items_user_ingredient ON pantry_items(user_id, ingredient_id);
CREATE INDEX idx_pantry_items_ingredient_user ON pantry_items(ingredient_id, user_id);

-- Create helper functions
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
  SELECT 
    rpm.recipe_id,
    rpm.title,
    rpm.match_percentage,
    rpm.matching_ingredients,
    rpm.total_ingredients
  FROM recipe_pantry_matches rpm
  WHERE rpm.user_id = p_user_id
  ORDER BY rpm.match_percentage DESC;
END;
$$ LANGUAGE plpgsql;

-- Create refresh function and triggers
CREATE OR REPLACE FUNCTION refresh_recipe_pantry_matches()
RETURNS trigger AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY recipe_pantry_matches;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

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

-- Add indexes for ingredient searching
CREATE INDEX idx_ingredients_normalized_name ON ingredients(normalized_name);
CREATE INDEX idx_ingredients_aliases ON ingredients USING gin(aliases);

-- Add GIN index for JSON searching
CREATE INDEX idx_user_preferences_gin ON user_preferences USING gin(preferences);

-- Add indexes for common queries
CREATE INDEX idx_user_recipe_interactions_user ON user_recipe_interactions(user_id, interaction_type);
CREATE INDEX idx_user_recipe_interactions_recipe ON user_recipe_interactions(recipe_id, interaction_type);

-- Add indexes for refresh tokens
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);

-- Add indexes for common queries
CREATE INDEX idx_recipes_title ON recipes USING gin(to_tsvector('english', title));
CREATE INDEX idx_recipes_created_at ON recipes(created_at DESC);
CREATE INDEX idx_recipes_total_time ON recipes(total_time) 
  WHERE total_time <= 30; -- Quick recipes are often queried

-- Add trigger to maintain updated_at
CREATE OR REPLACE FUNCTION update_recipe_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_recipe_timestamp
  BEFORE UPDATE ON recipes
  FOR EACH ROW
  EXECUTE FUNCTION update_recipe_timestamp();