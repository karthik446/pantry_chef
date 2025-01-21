-- Remove category_id from ingredients
ALTER TABLE public.ingredients 
DROP COLUMN category_id;

-- Drop the categories table since it's no longer needed
DROP TABLE public.categories;

-- Create nutrient_values table
CREATE TABLE public.nutrient_values (
    ingredient_id uuid PRIMARY KEY REFERENCES ingredients(id) ON DELETE CASCADE,
    caloric_value decimal,
    fat decimal,
    saturated_fats decimal,
    monounsaturated_fats decimal,
    polyunsaturated_fats decimal,
    carbohydrates decimal,
    sugars decimal,
    protein decimal,
    dietary_fiber decimal,
    cholesterol decimal,
    sodium decimal,
    water decimal,
    vitamin_a decimal,
    vitamin_b1 decimal,
    vitamin_b11 decimal,
    vitamin_b12 decimal,
    vitamin_b2 decimal,
    vitamin_b3 decimal,
    vitamin_b5 decimal,
    vitamin_b6 decimal,
    vitamin_c decimal,
    vitamin_d decimal,
    vitamin_e decimal,
    vitamin_k decimal,
    calcium decimal,
    copper decimal,
    iron decimal,
    magnesium decimal,
    manganese decimal,
    phosphorus decimal,
    potassium decimal,
    selenium decimal,
    zinc decimal,
    nutrition_density decimal,
    created_at timestamptz DEFAULT now()
);

-- Add index for better query performance
CREATE INDEX idx_nutrient_values_ingredient_id ON public.nutrient_values(ingredient_id);