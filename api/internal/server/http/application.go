package server

import (
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/token"
	"github.com/karthik446/pantry_chef/api/internal/server/service"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type application struct {
	config      *config.Config
	store       *store.Storage
	logger      *zap.SugaredLogger
	tokenGen    token.Generator
	authMid     *AuthMiddleware
	authService *service.AuthService
}

func NewApplication(cfg *config.Config, store *store.Storage, logger *zap.SugaredLogger) (*application, error) {
	tokenGen := token.NewJWTGenerator(token.Config{
		AccessTokenDuration:  15 * time.Minute,
		RefreshTokenDuration: 7 * 24 * time.Hour,
		SigningKey:           []byte(cfg.JWT.Secret),
	})

	authService := service.NewAuthService(tokenGen, store.Users, store.Tokens)

	return &application{
		config:      cfg,
		store:       store,
		logger:      logger,
		tokenGen:    tokenGen,
		authMid:     NewAuthMiddleware(tokenGen),
		authService: authService,
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

	r.Route("/v1", func(r chi.Router) {
		// Public routes
		r.Get("/health", app.healthCheckHandler)
		r.Get("/ready", app.readinessCheckHandler)

		// Auth routes
		r.Post("/auth/login", app.loginHandler)
		r.Post("/auth/refresh", app.refreshTokenHandler)

		// Protected routes
		r.Group(func(r chi.Router) {
			// Apply auth middleware to all routes in this group
			r.Use(app.authMid.Authenticate)

			// Ingredients routes
			r.Route("/ingredients", func(r chi.Router) {
				r.Get("/", app.listIngredientsHandler)

				// Admin only routes
				r.Group(func(r chi.Router) {
					r.Use(app.authMid.RequireRole("admin"))
					r.Post("/", app.createIngredientHandler)
					r.Put("/{id}", app.updateIngredientHandler)
					r.Delete("/{id}", app.deleteIngredientHandler)
				})
			})

			// Logout (requires auth)
			r.Post("/auth/logout", app.logoutHandler)
			r.Post("/auth/logout/all", app.logoutAllHandler)
		})
	})

	return r
}
