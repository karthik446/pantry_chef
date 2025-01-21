// src/routes/users.ts
import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { UserRepo, PantryRepo } from '../repositories';
import { requireAuth } from '../middleware/auth';
import { logError, logInfo } from '../utils/logger';
import { pantryRoutes } from './pantry';

interface UserParams {
  userId: string;
}

interface UpdatePreferencesBody {
  spice_level?: number;
  dietary_restrictions?: string[];
  favorite_cuisines?: string[];
}

export function userRoutes(userRepo: UserRepo, pantryRepo: PantryRepo) {
  return async function (fastify: FastifyInstance) {
    fastify.addHook('preHandler', requireAuth);

    // Register pantry routes with its repository
    fastify.register(pantryRoutes(pantryRepo));

    // Get user preferences
    fastify.get(
      '/:userId/preferences',
      async (request: FastifyRequest<{ Params: UserParams }>, reply: FastifyReply) => {
        try {
          const { userId } = request.params;

          // Check authorization
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({
              error: 'Not authorized to view other users preferences',
            });
          }

          const preferences = await userRepo.findById(userId);

          if (!preferences) {
            logInfo('No preferences found for user', { userId });
            return reply.code(404).send({
              message: 'No preferences found for this user',
            });
          }

          return reply.send(preferences);
        } catch (error) {
          logError('Error fetching user preferences', error);
          return reply.code(500).send({ error: 'Internal server error' });
        }
      },
    );

    // Update user preferences
    fastify.put(
      '/:userId/preferences',
      async (
        request: FastifyRequest<{
          Params: UserParams;
          Body: UpdatePreferencesBody;
        }>,
        reply: FastifyReply,
      ) => {
        try {
          const { userId } = request.params;

          // Check authorization
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({
              error: 'Not authorized to update other users preferences',
            });
          }

          const updated = await userRepo.updatePreferences(userId, request.body);
          return reply.send(updated);
        } catch (error) {
          logError('Error updating user preferences', error);
          return reply.code(500).send({ error: 'Internal server error' });
        }
      },
    );

    // Get user's favorite recipes
    fastify.get(
      '/:userId/recipes',
      async (request: FastifyRequest<{ Params: UserParams }>, reply: FastifyReply) => {
        try {
          const { userId } = request.params;

          // Check authorization
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({
              error: 'Not authorized to view other users recipes',
            });
          }

          const favorites = await userRepo.getFavorites(userId);

          if (!favorites || favorites.length === 0) {
            logInfo('No favorite recipes found for user', { userId });
            return reply.code(404).send({
              message: 'No favorite recipes found for this user',
            });
          }

          return reply.send(favorites.map((item) => item.recipes));
        } catch (error) {
          logError('Error fetching user favorites', error);
          return reply.code(500).send({ error: 'Internal server error' });
        }
      },
    );

    // Add favorite recipe
    fastify.post(
      '/:userId/recipes/:recipeId',
      async (
        request: FastifyRequest<{
          Params: UserParams & { recipeId: string };
        }>,
        reply: FastifyReply,
      ) => {
        try {
          const { userId, recipeId } = request.params;

          // Check authorization
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({
              error: 'Not authorized to modify other users favorites',
            });
          }

          await userRepo.addFavorite(userId, recipeId);
          return reply.code(201).send();
        } catch (error) {
          logError('Error adding favorite recipe', error);
          return reply.code(500).send({ error: 'Internal server error' });
        }
      },
    );

    // Remove favorite recipe
    fastify.delete(
      '/:userId/recipes/:recipeId',
      async (
        request: FastifyRequest<{
          Params: UserParams & { recipeId: string };
        }>,
        reply: FastifyReply,
      ) => {
        try {
          const { userId, recipeId } = request.params;

          // Check authorization
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({
              error: 'Not authorized to modify other users favorites',
            });
          }

          await userRepo.removeFavorite(userId, recipeId);
          return reply.code(204).send();
        } catch (error) {
          logError('Error removing favorite recipe', error);
          return reply.code(500).send({ error: 'Internal server error' });
        }
      },
    );
  };
}
