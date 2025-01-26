package server

import (
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type application struct {
	config *config.Config
	store  *store.Storage
	logger *zap.SugaredLogger
}

func NewApplication(store *store.Storage, logger *zap.SugaredLogger) *application {
	return &application{
		store:  store,
		logger: logger,
	}
}

func (app *application) Mount() *chi.Mux {
	r := chi.NewRouter()

	// Middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	r.Route("/v1", func(r chi.Router) {
		r.Get("/health", app.healthCheckHandler)
		r.Get("/ready", app.readinessCheckHandler)

		r.Route("/ingredients", func(r chi.Router) {
			r.Get("/", app.listIngredientsHandler)
			r.Post("/", app.createIngredientHandler)

			r.Route("/{id}", func(r chi.Router) {
				r.Get("/", app.listIngredientsHandler)
				r.Put("/", app.updateIngredientHandler)
				r.Delete("/", app.deleteIngredientHandler)
			})
		})
	})

	return r
}
