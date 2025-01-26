-- Drop triggers first
DROP TRIGGER IF EXISTS refresh_matches_pantry ON pantry_items;
DROP TRIGGER IF EXISTS refresh_matches_recipe ON recipe_ingredients;
DROP TRIGGER IF EXISTS refresh_matches_recipes ON recipes;

-- Drop functions
DROP FUNCTION IF EXISTS refresh_recipe_pantry_matches();
DROP FUNCTION IF EXISTS calculate_pantry_match(UUID);

-- Drop materialized view and indexes
DROP MATERIALIZED VIEW IF EXISTS recipe_pantry_matches;

-- Drop tables in correct order (respect foreign keys)
DROP TABLE IF EXISTS user_recipe_views;
DROP TABLE IF EXISTS user_search_history;
DROP TABLE IF EXISTS user_favorites;
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS pantry_items;
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS users;

-- Drop custom types
DROP TYPE IF EXISTS user_role;

-- Drop extensions
DROP EXTENSION IF EXISTS "uuid-ossp";
