// src/routes/pantry.ts
import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { PantryRepo } from '../repositories';
import { requireAuth } from '../middleware/auth';
import { logError } from '../utils/logger';

interface PantryParams {
  userId: string;
}

export function pantryRoutes(repository: PantryRepo) {
  return async function (fastify: FastifyInstance) {
    fastify.addHook('preHandler', requireAuth);

    fastify.get(
      '/:userId/pantry',
      async (request: FastifyRequest<{ Params: PantryParams }>, reply: FastifyReply) => {
        try {
          const { userId } = request.params;

          // Check if user is requesting their own pantry or is admin
          if (userId !== request.user!.id && request.user!.role !== 'admin') {
            return reply.code(403).send({ error: 'Not authorized to view other users pantry' });
          }

          const items = await repository.findByUser(userId);
          return reply.send(items);
        } catch (error) {
          logError('Error fetching pantry items', error);
          return reply.code(500).send({ error: 'Failed to fetch pantry items' });
        }
      },
    );

    // Add other pantry routes with userId parameter
    // POST /:userId/pantry
    // PUT /:userId/pantry/:itemId
    // DELETE /:userId/pantry/:itemId
  };
}
