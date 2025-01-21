import 'dotenv/config';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { RecipeRepo, UserRepo, PantryRepo, IngredientRepo } from './repositories';
import { supabase } from './lib/supabaseClient';
import { initLogger } from './utils/logger';
import { authRoutes } from './routes/auth';
import { userRoutes } from './routes/users';
import { recipeRoutes } from './routes/recipes';
import { ingredientRoutes } from './routes/ingredients';
import { swaggerOptions, swaggerUiOptions } from './swagger';

const app = Fastify({
  logger: {
    transport: {
      target: 'pino-pretty',
      options: {
        translateTime: 'HH:MM:ss Z',
        ignore: 'pid,hostname',
      },
    },
  },
});

initLogger(app.log);

async function start() {
  try {
    // Initialize repositories
    const repositories = {
      recipe: new RecipeRepo(supabase),
      user: new UserRepo(supabase),
      pantry: new PantryRepo(supabase),
      ingredient: new IngredientRepo(supabase),
    };

    // Register plugins
    await app.register(cors, { origin: true });
    await app.register(swagger, swaggerOptions);
    await app.register(swaggerUi, swaggerUiOptions);

    // Register routes
    app.get('/health', async () => ({ status: 'ok' }));

    await app.register(
      async (instance) => {
        instance.register(authRoutes, { prefix: '/auth' });
        instance.register(userRoutes(repositories.user, repositories.pantry), { prefix: '/users' });
        instance.register(recipeRoutes(repositories.recipe, repositories.ingredient), {
          prefix: '/recipes',
        });
        instance.register(ingredientRoutes(repositories.ingredient), { prefix: '/ingredients' });
      },
      { prefix: '/api' },
    );

    await app.listen({
      port: Number(process.env.PORT) || 8000,
      host: '0.0.0.0',
    });

    console.log(`Server running at http://localhost:${process.env.PORT || 8000}`);
    console.log('Documentation available at /documentation');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();
