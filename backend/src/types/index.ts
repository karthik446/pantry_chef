import { Database } from './supabase';

export type Tables = Database['public']['Tables'];

export type Recipe = Tables['recipes']['Row'];
export type RecipeInsert = Tables['recipes']['Insert'];
export type RecipeUpdate = Tables['recipes']['Update'];

export type RecipeIngredient = Tables['recipe_ingredients']['Row'] & {
  ingredients?: {
    name: string;
  };
};

export type User = Tables['users']['Row'];
export type UserPreferences = Tables['user_preferences']['Row'];

export type PantryItem = Tables['pantry_items']['Row'] & {
  ingredients?: {
    name: string;
  };
};

export type Category = Tables['categories']['Row'];
export type Ingredient = Tables['ingredients']['Row'];

// DTOs
export interface RecipeIngredientDTO {
  name: string; // Changed from ingredient_id
  quantity: number;
  unit: string;
}

export interface CreateRecipeDTO {
  title: string;
  instructions: string;
  prep_time: number;
  cook_time: number;
  servings: number;
  ingredients?: RecipeIngredientDTO[];
}

export interface UpdateRecipeDTO {
  title?: string;
  instructions?: string;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  source_url?: string;
  ingredients?: RecipeIngredientDTO[];
}
export interface UpdateRecipeDTO {
  title?: string;
  instructions?: string;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  ingredients?: RecipeIngredientDTO[];
}

// Make sure all properties are optional for updates
export type UpdateRecipeParams = Omit<UpdateRecipeDTO, 'ingredients'>;

export interface CreateIngredientDTO {
  name: string;
}
