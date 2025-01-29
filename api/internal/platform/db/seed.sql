-- Create users
INSERT INTO users (id, user_number, password_hash, role) VALUES 
    ('00000000-0000-0000-0000-000000000000', '0000000000', '$2a$10$rW5wWqbBnT8LxI7jRUg8OuU.XHvv.R5C8zKkVhD3CSWSMXo/bKmfq', 'admin'),
    ('11111111-1111-1111-1111-111111111111', '1111111111', '$2a$10$rW5wWqbBnT8LxI7jRUg8OuU.XHvv.R5C8zKkVhD3CSWSMXo/bKmfq', 'user'),
    ('22222222-2222-2222-2222-222222222222', '2222222222', '$2a$10$rW5wWqbBnT8LxI7jRUg8OuU.XHvv.R5C8zKkVhD3CSWSMXo/bKmfq', 'user')
ON CONFLICT (user_number) DO NOTHING;

-- Add ingredients
INSERT INTO ingredients (name, normalized_name, aliases) VALUES 
    ('Salt', 'salt', ARRAY['table salt', 'sea salt']),
    ('Black Pepper', 'pepper', ARRAY['ground black pepper', 'peppercorns']),
    ('Olive Oil', 'oil', ARRAY['extra virgin olive oil', 'EVOO']),
    ('Garlic', 'garlic', ARRAY['garlic cloves', 'minced garlic']),
    ('Onion', 'onion', ARRAY['yellow onion', 'white onion', 'red onion']),
    ('Tomato', 'tomato', ARRAY['roma tomato', 'cherry tomato']),
    ('Potato', 'potato', ARRAY['russet potato', 'yukon gold']),
    ('Carrot', 'carrot', ARRAY['baby carrots']),
    ('Rice', 'rice', ARRAY['white rice', 'brown rice', 'jasmine rice']),
    ('Pasta', 'pasta', ARRAY['spaghetti', 'penne', 'fettuccine']),
    ('Ground Beef', 'beef', ARRAY['minced beef', 'hamburger meat']),
    ('Chicken Breast', 'chicken', ARRAY['boneless chicken breast', 'chicken fillets']);


-- Add some pantry items for users
INSERT INTO pantry_items (user_id, ingredient_id, quantity, unit) 
SELECT 
    '11111111-1111-1111-1111-111111111111',
    ingredients.id,
    CASE ingredients.name
        WHEN 'Salt' THEN 500
        WHEN 'Black Pepper' THEN 100
        WHEN 'Olive Oil' THEN 750
        WHEN 'Garlic' THEN 200
        WHEN 'Onion' THEN 500
        WHEN 'Pasta' THEN 1000
    END,
    CASE ingredients.name
        WHEN 'Salt' THEN 'g'::measurement_unit
        WHEN 'Black Pepper' THEN 'g'::measurement_unit
        WHEN 'Olive Oil' THEN 'ml'::measurement_unit
        WHEN 'Garlic' THEN 'g'::measurement_unit
        WHEN 'Onion' THEN 'g'::measurement_unit
        WHEN 'Pasta' THEN 'g'::measurement_unit
    END
FROM ingredients
WHERE ingredients.name IN ('Salt', 'Black Pepper', 'Olive Oil', 'Garlic', 'Onion', 'Pasta');

-- Add different pantry items for second user
INSERT INTO pantry_items (user_id, ingredient_id, quantity, unit) 
SELECT 
    '22222222-2222-2222-2222-222222222222',
    ingredients.id,
    CASE ingredients.name
        WHEN 'Rice' THEN 1000
        WHEN 'Chicken Breast' THEN 500
        WHEN 'Carrot' THEN 300
        WHEN 'Salt' THEN 250
        WHEN 'Garlic' THEN 100
    END,
    CASE ingredients.name
        WHEN 'Rice' THEN 'g'::measurement_unit
        WHEN 'Chicken Breast' THEN 'g'::measurement_unit
        WHEN 'Carrot' THEN 'g'::measurement_unit
        WHEN 'Salt' THEN 'g'::measurement_unit
        WHEN 'Garlic' THEN 'g'::measurement_unit
    END
FROM ingredients
WHERE ingredients.name IN ('Rice', 'Chicken Breast', 'Carrot', 'Salt', 'Garlic');

-- Add recipes
INSERT INTO recipes (title, instructions, prep_time, cook_time, total_time, servings, source_url) VALUES 
    ('Basic Pasta Aglio e Olio', 
     E'1. Boil water\n2. Cook pasta\n3. Sauté garlic in olive oil\n4. Combine and serve', 
     10, 15, 25, 4,
     'https://example.com/pasta-aglio-olio'),
    
    ('Simple Chicken Rice', 
     E'1. Cook rice\n2. Season chicken\n3. Cook chicken\n4. Serve together', 
     15, 25, 40, 4,
     'https://example.com/chicken-rice'),
    
    ('Beef and Potato Stew', 
     E'1. Brown beef\n2. Add vegetables\n3. Simmer with stock\n4. Season and serve', 
     20, 60, 80, 6,
     'https://example.com/beef-stew')
ON CONFLICT DO NOTHING;

-- Add recipe ingredients for Pasta Aglio e Olio
WITH recipe AS (SELECT id FROM recipes WHERE title = 'Basic Pasta Aglio e Olio')
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
SELECT 
    recipe.id,
    ingredients.id,
    CASE ingredients.name
        WHEN 'Pasta' THEN 500
        WHEN 'Garlic' THEN 30
        WHEN 'Olive Oil' THEN 60
        WHEN 'Salt' THEN 5
        WHEN 'Black Pepper' THEN 2
    END,
    CASE ingredients.name
        WHEN 'Pasta' THEN 'g'::measurement_unit
        WHEN 'Garlic' THEN 'g'::measurement_unit
        WHEN 'Olive Oil' THEN 'ml'::measurement_unit
        WHEN 'Salt' THEN 'g'::measurement_unit
        WHEN 'Black Pepper' THEN 'g'::measurement_unit
    END
FROM recipe, ingredients
WHERE ingredients.name IN ('Pasta', 'Garlic', 'Olive Oil', 'Salt', 'Black Pepper');

-- Add recipe ingredients for Simple Chicken Rice
WITH recipe AS (SELECT id FROM recipes WHERE title = 'Simple Chicken Rice')
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
SELECT 
    recipe.id,
    ingredients.id,
    CASE ingredients.name
        WHEN 'Rice' THEN 400
        WHEN 'Chicken Breast' THEN 600
        WHEN 'Garlic' THEN 20
        WHEN 'Salt' THEN 5
        WHEN 'Black Pepper' THEN 2
    END,
    CASE ingredients.name
        WHEN 'Rice' THEN 'g'::measurement_unit
        WHEN 'Chicken Breast' THEN 'g'::measurement_unit
        WHEN 'Garlic' THEN 'g'::measurement_unit
        WHEN 'Salt' THEN 'g'::measurement_unit
        WHEN 'Black Pepper' THEN 'g'::measurement_unit
    END
FROM recipe, ingredients
WHERE ingredients.name IN ('Rice', 'Chicken Breast', 'Garlic', 'Salt', 'Black Pepper');

-- Refresh materialized view
REFRESH MATERIALIZED VIEW recipe_pantry_matches;


INSERT INTO users (id, user_number, password_hash, role, is_active) 
    VALUES (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',  -- fixed UUID for testing
        1234567890,                             -- user number
        '$2a$10$RC0HaTpwaa9IP2jyD1bjuuQHGSfAiZNGKMr1KFQ9kTHLj1idwYvb2',  -- 'password123'
        'admin',                                  -- role
        true                                      -- is_active
    );