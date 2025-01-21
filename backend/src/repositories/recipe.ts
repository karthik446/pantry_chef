import { BaseRepository } from './base';
import { Recipe, CreateRecipeDTO, UpdateRecipeDTO } from '../types';

export class RecipeRepo extends BaseRepository {
  async findAll() {
    const { data, error } = await this.client.from('recipes').select(`
        *,
        recipe_ingredients (
          ingredient_id,
          quantity,
          unit,
          ingredients:ingredient_id (
            name
          )
        )
      `);

    if (error) throw error;
    return data;
  }

  async findById(id: string) {
    const { data, error } = await this.client
      .from('recipes')
      .select(
        `
        *,
        recipe_ingredients (
          ingredient_id,
          quantity,
          unit,
          ingredients:ingredient_id (
            name
          )
        )
      `,
      )
      .eq('id', id)
      .single();

    if (error) throw error;
    return data;
  }

  async create(recipe: CreateRecipeDTO) {
    // Destructure ingredients out and only send recipe fields to Supabase
    const { ingredients, ...recipeData } = recipe;

    const { data, error } = await this.client.from('recipes').insert(recipeData).select().single();

    if (error) throw error;
    return data;
  }

  async findByIngredients(ingredientIds: string[]) {
    const { data, error } = await this.client.rpc('find_recipes_by_ingredients', {
      ingredient_ids: ingredientIds,
    });

    if (error) throw error;
    return data;
  }

  async findPopular() {
    const { data, error } = await this.client
      .from('recipes')
      .select(
        `
        *,
        favorite_count:user_favorites(count)
      `,
      )
      .order('favorite_count', { ascending: false })
      .limit(10);

    if (error) throw error;
    return data;
  }

  async addIngredients(
    recipeId: string,
    ingredients: Array<{ ingredient_id: string; quantity: number; unit: string }>,
  ) {
    const { error } = await this.client
      .from('recipe_ingredients')
      .insert(ingredients.map((i) => ({ ...i, recipe_id: recipeId })));

    if (error) throw error;
  }

  async updateIngredients(
    recipeId: string,
    ingredients: Array<{ ingredient_id: string; quantity: number; unit: string }>,
  ) {
    // Start a transaction
    const { error } = await this.client
      .from('recipe_ingredients')
      .delete()
      .eq('recipe_id', recipeId);

    if (error) throw error;

    return this.addIngredients(recipeId, ingredients);
  }

  async searchByTitle(query: string) {
    const { data, error } = await this.client
      .from('recipes')
      .select('*')
      .ilike('title', `%${query}%`);

    if (error) throw error;
    return data;
  }

  async findUrlsBySearchQuery(searchQuery: string) {
    // Split the search query into words and filter out short words
    const searchWords = searchQuery
      .toLowerCase()
      .split(' ')
      .filter((word) => word.length > 2);

    if (searchWords.length === 0) return [];

    const { data, error } = await this.client
      .from('recipes')
      .select('source_url, created_from_search_query')
      .not('created_from_search_query', 'is', null)
      .not('source_url', 'is', null);

    if (error) throw error;

    // Filter recipes where at least 2 search words match
    return data
      .filter((recipe: any) => {
        const existingWords = recipe.created_from_search_query.toLowerCase().split(' ');
        const matchingWords = searchWords.filter((word) =>
          existingWords.some((existing: any) => existing.includes(word)),
        );
        return matchingWords.length >= 2;
      })
      .map((recipe) => recipe.source_url);
  }

  // Add other recipe-specific methods...
}
