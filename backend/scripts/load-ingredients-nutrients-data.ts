import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import { readFile } from 'fs/promises';
import { join } from 'path';
import { parse } from 'csv-parse/sync';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from the root directory
dotenv.config({ path: join(__dirname, '..', '.env') });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_API_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase credentials in .env file');
}

const supabase = createClient(supabaseUrl, supabaseKey);

interface FoodData {
  food: string;
  'Caloric Value': string;
  Fat: string;
  'Saturated Fats': string;
  'Monounsaturated Fats': string;
  'Polyunsaturated Fats': string;
  Carbohydrates: string;
  Sugars: string;
  Protein: string;
  'Dietary Fiber': string;
  Cholesterol: string;
  Sodium: string;
  Water: string;
  'Vitamin A': string;
  'Vitamin B1': string;
  'Vitamin B11': string;
  'Vitamin B12': string;
  'Vitamin B2': string;
  'Vitamin B3': string;
  'Vitamin B5': string;
  'Vitamin B6': string;
  'Vitamin C': string;
  'Vitamin D': string;
  'Vitamin E': string;
  'Vitamin K': string;
  Calcium: string;
  Copper: string;
  Iron: string;
  Magnesium: string;
  Manganese: string;
  Phosphorus: string;
  Potassium: string;
  Selenium: string;
  Zinc: string;
  'Nutrition Density': string;
}

const COLUMN_MAPPINGS = {
  'Caloric Value': 'caloric_value',
  Fat: 'fat',
  'Saturated Fats': 'saturated_fats',
  'Monounsaturated Fats': 'monounsaturated_fats',
  'Polyunsaturated Fats': 'polyunsaturated_fats',
  Carbohydrates: 'carbohydrates',
  Sugars: 'sugars',
  Protein: 'protein',
  'Dietary Fiber': 'dietary_fiber',
  Cholesterol: 'cholesterol',
  Sodium: 'sodium',
  Water: 'water',
  'Vitamin A': 'vitamin_a',
  'Vitamin B1': 'vitamin_b1',
  'Vitamin B11': 'vitamin_b11',
  'Vitamin B12': 'vitamin_b12',
  'Vitamin B2': 'vitamin_b2',
  'Vitamin B3': 'vitamin_b3',
  'Vitamin B5': 'vitamin_b5',
  'Vitamin B6': 'vitamin_b6',
  'Vitamin C': 'vitamin_c',
  'Vitamin D': 'vitamin_d',
  'Vitamin E': 'vitamin_e',
  'Vitamin K': 'vitamin_k',
  Calcium: 'calcium',
  Copper: 'copper',
  Iron: 'iron',
  Magnesium: 'magnesium',
  Manganese: 'manganese',
  Phosphorus: 'phosphorus',
  Potassium: 'potassium',
  Selenium: 'selenium',
  Zinc: 'zinc',
  'Nutrition Density': 'nutrition_density',
} as const;

const BATCH_SIZE = 100; // Adjust based on your needs

async function processCSV() {
  const filePath = join(__dirname, 'csvs', 'FOOD-DATA-GROUP5.csv');
  const fileContent = await readFile(filePath, 'utf-8');

  return parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  });
}

async function loadIngredientsAndNutrients() {
  try {
    // Process CSV data
    const foodData = (await processCSV()) as FoodData[];
    console.log(`Processing ${foodData.length} ingredients...`);

    // Process in batches
    for (let i = 0; i < foodData.length; i += BATCH_SIZE) {
      const batch = foodData.slice(i, i + BATCH_SIZE);

      // Insert ingredients batch
      const { data: ingredientData, error: ingredientError } = await supabase
        .from('ingredients')
        .upsert(batch.map((food) => ({ name: food.food })))
        .select();

      if (ingredientError) {
        console.error('Error inserting ingredients batch:', ingredientError);
        continue;
      }

      // Prepare nutrient values batch
      const nutrientValuesBatch = ingredientData.map((ingredient, index) => ({
        ingredient_id: ingredient.id,
        ...Object.entries(COLUMN_MAPPINGS).reduce(
          (acc, [csvKey, dbKey]) => ({
            ...acc,
            [dbKey]: parseFloat(batch[index][csvKey as keyof FoodData]) || 0,
          }),
          {},
        ),
      }));

      // Insert nutrient values batch
      const { error: nutrientValueError } = await supabase
        .from('nutrient_values')
        .upsert(nutrientValuesBatch);

      if (nutrientValueError) {
        console.error('Error inserting nutrient values batch:', nutrientValueError);
      } else {
        console.log(`Processed batch ${i / BATCH_SIZE + 1}: ${batch.length} ingredients`);
      }
    }

    console.log('Data loading completed successfully');
  } catch (error) {
    console.error('Error loading data:', error);
  }
}

loadIngredientsAndNutrients();
