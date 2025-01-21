import { BaseRepository } from './base';
import { Ingredient, CreateIngredientDTO } from '../types';

export class IngredientRepo extends BaseRepository {
  async findAll() {
    const { data, error } = await this.client.from('ingredients').select(`
        *,
        categories:category_id (
          name
        )
      `);

    if (error) throw error;
    return data;
  }

  async findById(id: string) {
    const { data, error } = await this.client
      .from('ingredients')
      .select(
        `
        *,
        categories:category_id (
          name
        )
      `,
      )
      .eq('id', id)
      .single();

    if (error) throw error;
    return data;
  }

  async findClosestMatch(name: string): Promise<Ingredient | null> {
    const { data, error } = await this.client
      .from('ingredients')
      .select('*')
      .ilike('name', `%${name}%`)
      .limit(1);

    if (error) {
      throw error;
    }

    return data[0] || null;
  }
  async create(ingredient: CreateIngredientDTO) {
    const { data, error } = await this.client
      .from('ingredients')
      .insert(ingredient)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async findByCategory(categoryId: string) {
    const { data, error } = await this.client
      .from('ingredients')
      .select('*')
      .eq('category_id', categoryId);

    if (error) throw error;
    return data;
  }

  async searchIngredients(queries: string[]) {
    // Get all ingredients first
    const { data: ingredients, error } = await this.client.from('ingredients').select('id, name');

    if (error) throw error;

    // Process each search term
    return queries.map((query) => {
      const normalizedQuery = query.toLowerCase().trim();

      // Try different matching strategies
      const match = ingredients?.find((ingredient) => {
        const name = ingredient.name.toLowerCase();

        // Exact match
        if (name === normalizedQuery) return true;

        // Contains match
        if (name.includes(normalizedQuery)) return true;

        // Remove plural 's' and try again
        if (normalizedQuery.endsWith('s')) {
          const singular = normalizedQuery.slice(0, -1);
          if (name.includes(singular)) return true;
        }

        // Add more matching strategies here as needed
        // For example: handle common abbreviations, synonyms, etc.

        return false;
      });

      return {
        query,
        match: match
          ? {
              id: match.id,
              name: match.name,
            }
          : null,
      };
    });
  }
}
