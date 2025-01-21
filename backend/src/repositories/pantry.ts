import { BaseRepository } from './base';
import { PantryItem } from '../types';

export class PantryRepo extends BaseRepository {
  async findByUser(userId: string) {
    const { data, error } = await this.client
      .from('pantry_items')
      .select(
        `
        *,
        ingredients:ingredient_id (
          name,
          categories:category_id (
            name
          )
        )
      `,
      )
      .eq('user_id', userId);

    if (error) throw error;
    return data;
  }

  async addItem(userId: string, item: PantryItem) {
    const { data, error } = await this.client
      .from('pantry_items')
      .insert({ ...item, user_id: userId })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async updateItem(id: string, userId: string, updates: Partial<PantryItem>) {
    const { data, error } = await this.client
      .from('pantry_items')
      .update(updates)
      .eq('id', id)
      .eq('user_id', userId)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async removeItem(id: string, userId: string) {
    const { error } = await this.client
      .from('pantry_items')
      .delete()
      .eq('id', id)
      .eq('user_id', userId);

    if (error) throw error;
  }

  async findMatchingRecipes(userId: string) {
    const { data, error } = await this.client.rpc('find_recipes_by_pantry', { user_id: userId });

    if (error) throw error;
    return data;
  }
}
