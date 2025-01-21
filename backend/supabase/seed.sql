-- supabase/seed.sql

DO $$ 
DECLARE 
    user_record RECORD;
    recipe RECORD;
BEGIN
    -- Clean up existing data first    
    -- Create regular user (admin already exists from migration)
    INSERT INTO public.users (email, role) 
    VALUES ('user@example.com', 'user');

    -- Rest of your seed file remains exactly the same
    -- Create 2 recipes
    INSERT INTO public.recipes (title, instructions, prep_time, cook_time, servings) VALUES
    ('Simple Grilled Chicken', 
     'Season chicken breast. Grill until cooked through. Rest for 5 minutes before serving.',
     10, 15, 2),
    ('Baked Salmon',
     'Season salmon fillet. Bake at 400°F for 12-15 minutes until flaky.',
     5, 15, 2);

    -- Add recipe ingredients
    WITH recipe_ids AS (
        SELECT id, title FROM public.recipes
    ),
    ingredient_ids AS (
        SELECT id, name FROM public.ingredients
    )
    INSERT INTO public.recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
    SELECT 
        r.id,
        i.id,
        200,
        'g'
    FROM recipe_ids r
    JOIN ingredient_ids i ON 
        (r.title LIKE '%Chicken%' AND i.name = 'Chicken Breast') OR
        (r.title LIKE '%Salmon%' AND i.name = 'Salmon Fillet');

    -- Add preferences for users
    INSERT INTO public.user_preferences (user_id, spice_level)
    SELECT id, 3 FROM public.users;

    -- Add one favorite recipe for each user
    WITH user_ids AS (
        SELECT id FROM public.users
    ),
    recipe_ids AS (
        SELECT id FROM public.recipes
    )
    INSERT INTO public.user_favorites (user_id, recipe_id)
    SELECT 
        u.id,
        r.id
    FROM user_ids u
    CROSS JOIN recipe_ids r
    LIMIT 2;

END $$;