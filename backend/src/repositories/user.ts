import { BaseRepository } from './base';
import { User, UserPreferences } from '../types';

export class UserRepo extends BaseRepository {
  async findById(id: string) {
    const { data, error } = await this.client
      .from('users')
      .select(
        `
        *,
        user_preferences (*)
      `,
      )
      .eq('id', id)
      .single();

    if (error) throw error;
    return data;
  }

  async updatePreferences(userId: string, preferences: Partial<UserPreferences>) {
    const { data, error } = await this.client
      .from('user_preferences')
      .upsert({ user_id: userId, ...preferences })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async getFavorites(userId: string) {
    const { data, error } = await this.client
      .from('user_favorites')
      .select(
        `
        recipes:recipe_id (*)
      `,
      )
      .eq('user_id', userId);

    if (error) throw error;
    return data;
  }

  async addFavorite(userId: string, recipeId: string) {
    const { error } = await this.client
      .from('user_favorites')
      .upsert({ user_id: userId, recipe_id: recipeId });

    if (error) throw error;
  }

  async removeFavorite(userId: string, recipeId: string) {
    const { error } = await this.client
      .from('user_favorites')
      .delete()
      .eq('user_id', userId)
      .eq('recipe_id', recipeId);

    if (error) throw error;
  }
}
