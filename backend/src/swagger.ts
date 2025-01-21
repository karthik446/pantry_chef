// src/swagger.ts
export const swaggerOptions = {
  swagger: {
    info: {
      title: 'Kitchen Companion API',
      description: 'API documentation for Kitchen Companion',
      version: '1.0.0',
    },
    host: 'localhost:8000',
    schemes: ['http'],
    consumes: ['application/json'],
    produces: ['application/json'],
    tags: [
      { name: 'users', description: 'User related end-points' },
      { name: 'recipes', description: 'Recipe related end-points' },
      { name: 'ingredients', description: 'Ingredient related end-points' },
      { name: 'pantry', description: 'Pantry related end-points' },
    ],
  },
};

export const swaggerUiOptions = {
  routePrefix: '/documentation',
  exposeRoute: true,
};
