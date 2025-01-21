// src/routes/index.ts
import { FastifyInstance } from 'fastify';
import { recipeRoutes } from './recipes';
import { userRoutes } from './users';
import { pantryRoutes } from './pantry';
import { ingredientRoutes } from './ingredients';
import { RecipeRepo, UserRepo, PantryRepo, IngredientRepo } from '../repositories';
import { supabase } from '../lib/supabaseClient';

// deno-lint-ignore require-await
export async function routes(app: FastifyInstance) {
  // Initialize repositories
  const repositories = {
    recipe: new RecipeRepo(supabase),
    user: new UserRepo(supabase),
    pantry: new PantryRepo(supabase),
    ingredient: new IngredientRepo(supabase),
  };

  // Register routes with repositories
  app.register(recipeRoutes(repositories.recipe, repositories.ingredient), { prefix: '/recipes' });
  app.register(userRoutes(repositories.user, repositories.pantry), { prefix: '/users' });
  app.register(ingredientRoutes(repositories.ingredient), { prefix: '/ingredients' });
}
