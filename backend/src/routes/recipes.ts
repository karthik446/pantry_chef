// src/routes/recipes.ts
import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { RecipeRepo, IngredientRepo } from '../repositories';
import { logError } from '../utils/logger';
import { recipeAdminRoutes } from './recipes.admin';

interface RecipeParams {
  id: string;
}

interface SearchRecipesQuery {
  ingredients?: string[];
  title?: string;
}

export function recipeRoutes(repository: RecipeRepo, ingredientRepository: IngredientRepo) {
  return async function (fastify: FastifyInstance) {
    // Register admin routes
    fastify.register(recipeAdminRoutes(repository, ingredientRepository), { prefix: '/admin' });

    // Get all recipes
    fastify.get('/', async (_request, reply: FastifyReply) => {
      try {
        const recipes = await repository.findAll();
        return reply.send(recipes);
      } catch (error) {
        logError('Error fetching recipes', error);
        return reply.code(500).send({ error: 'Failed to fetch recipes' });
      }
    });

    // Get single recipe
    fastify.get(
      '/:id',
      async (request: FastifyRequest<{ Params: RecipeParams }>, reply: FastifyReply) => {
        try {
          const recipe = await repository.findById(request.params.id);
          if (!recipe) {
            return reply.code(404).send({ error: 'Recipe not found' });
          }
          return reply.send(recipe);
        } catch (error) {
          logError('Error fetching recipe', error);
          return reply.code(500).send({ error: 'Failed to fetch recipe' });
        }
      },
    );

    // Search recipes
    fastify.get(
      '/search',
      async (request: FastifyRequest<{ Querystring: SearchRecipesQuery }>, reply: FastifyReply) => {
        try {
          const { ingredients, title } = request.query;

          if (ingredients?.length) {
            const recipes = await repository.findByIngredients(ingredients);
            return reply.send(recipes);
          }

          if (title) {
            const recipes = await repository.searchByTitle(title);
            return reply.send(recipes);
          }

          return reply.code(400).send({ error: 'Missing search parameters' });
        } catch (error) {
          logError('Error searching recipes', error);
          return reply.code(500).send({ error: 'Failed to search recipes' });
        }
      },
    );

    // Get popular recipes
    fastify.get('/popular', async (_request, reply: FastifyReply) => {
      try {
        const recipes = await repository.findPopular();
        return reply.send(recipes);
      } catch (error) {
        logError('Error fetching popular recipes', error);
        return reply.code(500).send({ error: 'Failed to fetch popular recipes' });
      }
    });
  };
}
