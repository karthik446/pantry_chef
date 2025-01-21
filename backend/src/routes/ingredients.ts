import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { IngredientRepo } from '../repositories';
import { logError } from '../utils/logger';

interface SearchIngredientsBody {
  ingredients: string[]; // array of ingredient names
}

interface IngredientMatch {
  query: string;
  match: {
    id: string;
    name: string;
  } | null;
}

export function ingredientRoutes(repository: IngredientRepo) {
  return async function (fastify: FastifyInstance) {
    fastify.post(
      '/search',
      {
        schema: {
          body: {
            type: 'object',
            required: ['ingredients'],
            properties: {
              ingredients: {
                type: 'array',
                items: { type: 'string' },
              },
            },
          },
        },
      },
      async (request: FastifyRequest<{ Body: SearchIngredientsBody }>, reply: FastifyReply) => {
        try {
          const { ingredients } = request.body;

          if (!ingredients || !Array.isArray(ingredients) || ingredients.length === 0) {
            return reply.code(400).send({ error: 'Invalid ingredients array' });
          }

          const results = await repository.searchIngredients(ingredients);

          // Check if any ingredients weren't found
          const notFound = results.filter((r) => r.match === null);
          if (notFound.length > 0) {
            return reply.code(404).send({
              error: 'Some ingredients not found',
              notFound: notFound.map((r) => r.query),
            });
          }

          return reply.send({
            matches: results.map((r) => ({
              query: r.query,
              id: r.match!.id,
              name: r.match!.name,
            })),
          });
        } catch (error) {
          logError('Error searching ingredients', error);
          return reply.code(500).send({ error: 'Failed to search ingredients' });
        }
      },
    );
  };
}
