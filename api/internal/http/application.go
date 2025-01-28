package http_server

import (
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/auth"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/health"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/ingredients"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/metrics"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/recipes"
	"github.com/karthik446/pantry_chef/api/internal/http/middlewares"
	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/token"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type application struct {
	config   *config.Config
	store    *store.Storage
	logger   *zap.SugaredLogger
	tokenGen token.Generator
	authMid  *middlewares.AuthMiddleware
}

func NewApplication(cfg *config.Config, store *store.Storage, logger *zap.SugaredLogger) (*application, error) {
	tokenGen := token.NewJWTGenerator(token.Config{
		AccessTokenDuration:  60 * time.Minute,
		RefreshTokenDuration: 7 * 24 * time.Hour,
		SigningKey:           []byte(cfg.JWT.Secret),
	})

	return &application{
		config:   cfg,
		store:    store,
		logger:   logger,
		tokenGen: tokenGen,
		authMid:  middlewares.NewAuthMiddleware(tokenGen),
	}, nil
}

func (app *application) Mount() *chi.Mux {
	r := chi.NewRouter()

	// Global middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	metricsService := metrics.NewMetricsService(app.store.Metrics)
	// Add metrics middleware globally
	metricsMid := middlewares.NewMetricsMiddleware(metricsService, app.logger)
	r.Use(metricsMid.Metrics)

	authService := auth.NewAuthService(app.tokenGen, app.store.Users, app.store.Tokens)

	authHandler := auth.NewAuthHandler(app.logger, authService)
	ingredientHandler := ingredients.NewIngredientHandler(app.logger, app.store.Ingredients)
	healthHandler := health.NewHealthHandler(app.logger)
	metricsHandler := metrics.NewMetricsHandler(metricsService, app.logger)
	recipeHandler := recipes.NewRecipeHandler(app.logger, app.store.Recipes)
	r.Route("/api/v1", func(r chi.Router) {
		// Public routes
		r.Get("/health", healthHandler.HealthCheckHandler)
		r.Get("/ready", healthHandler.ReadinessCheckHandler)

		// Auth routes
		r.Post("/auth/login", authHandler.Login)
		r.Post("/auth/refresh", authHandler.Refresh)

		// Protected routes
		r.Group(func(r chi.Router) {
			// Apply auth middleware to all routes in this group
			r.Use(app.authMid.Authenticate)

			// Ingredients routes
			r.Route("/ingredients", func(r chi.Router) {
				r.Get("/", ingredientHandler.List)

				// Admin only routes
				r.Group(func(r chi.Router) {
					r.Use(app.authMid.RequireRole("admin"))
					r.Post("/", ingredientHandler.Create)
					r.Put("/{id}", ingredientHandler.Update)
					r.Delete("/{id}", ingredientHandler.Delete)
				})
			})

			// Recipes routes
			r.Route("/recipes", func(r chi.Router) {
				r.Get("/", recipeHandler.List)

				// Admin only routes
				r.Group(func(r chi.Router) {
					r.Use(app.authMid.RequireRole("admin"))
					r.Get("/urlsBySearchQuery", recipeHandler.FindUrlsBySearchQuery)
					r.Post("/", recipeHandler.Create)
					r.Get("/{id}", recipeHandler.GetByID)
				})
			})

			// Logout (requires auth)
			r.Post("/auth/logout", authHandler.Logout)
			r.Post("/auth/logout/all", authHandler.LogoutAll)
		})

		// Admin routes
		r.Route("/admin", func(r chi.Router) {
			// First authenticate the user
			r.Use(app.authMid.Authenticate)
			// Then check if they're an admin
			r.Use(app.authMid.RequireRole("admin"))
			r.Get("/metrics", metricsHandler.GetMetrics)
		})
	})

	return r
}
