DO $$ 
DECLARE 
    test_user_id uuid;
    chicken_id uuid;
    garlic_id uuid;
    onion_id uuid;
    salt_id uuid;
    pepper_id uuid;
    olive_oil_id uuid;
    recipe_id uuid;
BEGIN
    -- Clean up existing data
    TRUNCATE public.users, public.ingredients, 
            public.recipes, public.recipe_ingredients, public.pantry_items CASCADE;

    -- Create test user
    INSERT INTO public.users (id, email, role) 
    VALUES (gen_random_uuid(), 'test@example.com', 'user')
    RETURNING id INTO test_user_id;

    -- Create basic ingredients
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Chicken Breast') RETURNING id INTO chicken_id;
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Garlic') RETURNING id INTO garlic_id;
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Onion') RETURNING id INTO onion_id;
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Salt') RETURNING id INTO salt_id;
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Black Pepper') RETURNING id INTO pepper_id;
    INSERT INTO public.ingredients (id, name) VALUES
    (gen_random_uuid(), 'Olive Oil') RETURNING id INTO olive_oil_id;

    -- Add ingredients to test user's pantry
    INSERT INTO public.pantry_items (user_id, ingredient_id, quantity, unit) VALUES
    (test_user_id, chicken_id, 500, 'g'),
    (test_user_id, garlic_id, 5, 'cloves'),
    (test_user_id, onion_id, 2, 'pieces'),
    (test_user_id, salt_id, 100, 'g'),
    (test_user_id, olive_oil_id, 500, 'ml');

    -- Create a recipe that should match most pantry items (5/6 ingredients = 83% match)
    INSERT INTO public.recipes (id, title, instructions, prep_time, cook_time, servings)
    VALUES (
        gen_random_uuid(),
        'Garlic Chicken with Onions',
        'Season chicken with salt and pepper. Sauté garlic and onions in olive oil. Add chicken and cook until done.',
        15,
        25,
        4
    ) RETURNING id INTO recipe_id;

    -- Add ingredients to recipe
    INSERT INTO public.recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES
    (recipe_id, chicken_id, 400, 'g'),
    (recipe_id, garlic_id, 4, 'cloves'),
    (recipe_id, onion_id, 1, 'piece'),
    (recipe_id, salt_id, 5, 'g'),
    (recipe_id, olive_oil_id, 30, 'ml'),
    (recipe_id, pepper_id, 2, 'g');

    -- Create another recipe with fewer matching ingredients (3/4 ingredients = 75% match)
    INSERT INTO public.recipes (id, title, instructions, prep_time, cook_time, servings)
    VALUES (
        gen_random_uuid(),
        'Simple Garlic Chicken',
        'Season chicken with salt. Sauté garlic in olive oil. Add chicken and cook until done.',
        10,
        20,
        2
    ) RETURNING id INTO recipe_id;

    -- Add ingredients to second recipe
    INSERT INTO public.recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES
    (recipe_id, chicken_id, 300, 'g'),
    (recipe_id, garlic_id, 2, 'cloves'),
    (recipe_id, salt_id, 3, 'g'),
    (recipe_id, olive_oil_id, 20, 'ml');

    -- Refresh the materialized view to include our new data
    REFRESH MATERIALIZED VIEW recipe_pantry_matches;

    -- Password is 'password123' hashed with bcrypt
    INSERT INTO users (id, user_number, password_hash, role, is_active) 
    VALUES (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',  -- fixed UUID for testing
        '1234567890',                             -- user number
        '$2a$10$Xc1CZxD.mh6jWCy2ABHdh.7QHChxd7c2R8YhWfFpK9APyaWqj5bqK',  -- 'password123'
        'admin',                                  -- role
        true                                      -- is_active
    );

END $$;