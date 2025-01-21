import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { RecipeRepo } from '../repositories';
import { requireAdmin } from '../middleware/auth';
import { logError } from '../utils/logger';
import { CreateRecipeDTO, UpdateRecipeDTO } from '../types';
import { IngredientRepo } from '../repositories';

interface RecipeParams {
  id: string;
}

export function recipeAdminRoutes(repository: RecipeRepo, ingredientRepository: IngredientRepo) {
  return async function (fastify: FastifyInstance) {
    // Add admin authentication to all routes
    fastify.addHook('preHandler', requireAdmin);

    // Create recipe
    fastify.post(
      '/',
      async (request: FastifyRequest<{ Body: CreateRecipeDTO }>, reply: FastifyReply) => {
        try {
          console.log('Creating recipe with body:', JSON.stringify(request.body, null, 2));

          const recipe = await repository.create(request.body);

          if (request.body.ingredients?.length) {
            console.log(
              'Processing ingredients:',
              JSON.stringify(request.body.ingredients, null, 2),
            );

            const ingredientsWithIds = await Promise.all(
              request.body.ingredients.map(async (ingredient) => {
                console.log('Finding match for ingredient:', ingredient.name);
                let matchingIngredient = await ingredientRepository.findClosestMatch(
                  ingredient.name,
                );

                if (!matchingIngredient) {
                  console.log('Creating new ingredient:', ingredient.name);
                  matchingIngredient = await ingredientRepository.create({
                    name: ingredient.name,
                  });
                  return {
                    quantity: ingredient.quantity,
                    unit: ingredient.unit,
                    ingredient_id: matchingIngredient!.id,
                  };
                }

                console.log('Using ingredient:', matchingIngredient);
                return {
                  quantity: ingredient.quantity,
                  unit: ingredient.unit,
                  ingredient_id: matchingIngredient.id,
                };
              }),
            );

            console.log(
              'Adding ingredients to recipe:',
              JSON.stringify(ingredientsWithIds, null, 2),
            );
            await repository.addIngredients(recipe.id, ingredientsWithIds);
          }

          return reply.code(201).send(recipe);
        } catch (error) {
          console.error('Detailed error:', error);
          logError('Error creating recipe', error);
          return reply.code(500).send({ error: 'Failed to create recipe' });
        }
      },
    );

    // Update recipe
    // fastify.put(
    //   '/:id',
    //   async (
    //     request: FastifyRequest<{
    //       Params: RecipeParams;
    //       Body: UpdateRecipeDTO;
    //     }>,
    //     reply: FastifyReply,
    //   ) => {
    //     try {
    //       const { id } = request.params;
    //       const recipe = await repository.findById(id);

    //       if (!recipe) {
    //         return reply.code(404).send({ error: 'Recipe not found' });
    //       }

    //       const updated = await repository.update(id, request.body);

    //       if (request.body.ingredients) {
    //         await repository.updateIngredients(id, request.body.ingredients);
    //       }

    //       return reply.send(updated);
    //     } catch (error) {
    //       logError('Error updating recipe', error);
    //       return reply.code(500).send({ error: 'Failed to update recipe' });
    //     }
    //   },
    // );

    // Delete recipe
    // fastify.delete(
    //   '/:id',
    //   async (request: FastifyRequest<{ Params: RecipeParams }>, reply: FastifyReply) => {
    //     try {
    //       const { id } = request.params;
    //       await repository.delete(id);
    //       return reply.code(204).send();
    //     } catch (error) {
    //       logError('Error deleting recipe', error);
    //       return reply.code(500).send({ error: 'Failed to delete recipe' });
    //     }
    //   },
    // );

    // Search for existing URLs with similar search queries
    fastify.get(
      '/urls',
      async (
        request: FastifyRequest<{
          Querystring: { search_query: string };
        }>,
        reply: FastifyReply,
      ) => {
        try {
          const { search_query } = request.query;

          if (!search_query) {
            return reply.code(400).send({ error: 'Search query is required' });
          }

          const urls = await repository.findUrlsBySearchQuery(search_query);
          return reply.send(urls);
        } catch (error) {
          logError('Error searching URLs', error);
          return reply.code(500).send({ error: 'Failed to search URLs' });
        }
      },
    );
  };
}
