import { BaseRepository } from './base';
import { Category } from '../types';

export class CategoryRepo extends BaseRepository {
  async findAll() {
    const { data, error } = await this.client.from('categories').select('*');

    if (error) throw error;
    return data;
  }

  async create(category: Category) {
    const { data, error } = await this.client.from('categories').insert(category).select().single();

    if (error) throw error;
    return data;
  }
}
