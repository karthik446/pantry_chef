package http_server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
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
	"github.com/prometheus/client_golang/prometheus/promhttp"
	amqp "github.com/rabbitmq/amqp091-go"
	"go.uber.org/zap"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

type application struct {
	config         *config.Config
	store          *store.Storage
	logger         *zap.SugaredLogger
	tokenGen       token.Generator
	authMid        *middlewares.AuthMiddleware
	serviceAuthMid *middlewares.ServiceAuthMiddleware
	rabbitConn     *amqp.Connection
}

func NewApplication(cfg *config.Config, store *store.Storage, logger *zap.SugaredLogger) (*application, error) {
	tokenGen := token.NewJWTGenerator(token.Config{
		AccessTokenDuration:  60 * time.Minute,
		RefreshTokenDuration: 7 * 24 * time.Hour,
		SigningKey:           []byte(cfg.JWT.Secret),
	})
	rabbitConn, err := amqp.Dial(cfg.RabbitMQ.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	// Add this log to check if the connection is established
	logger.Infof("RabbitMQ connection established: %v", rabbitConn != nil)

	// Initialize Kubernetes client
	k8sConfig, err := rest.InClusterConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to get k8s config: %w", err)
	}

	k8sClient, err := kubernetes.NewForConfig(k8sConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8s client: %w", err)
	}

	logger.Info("Initializing service auth middleware with k8s client")
	serviceAuthMid := middlewares.NewServiceAuthMiddleware(logger.Named("service_auth"), k8sClient)

	return &application{
		config:         cfg,
		store:          store,
		logger:         logger,
		tokenGen:       tokenGen,
		authMid:        middlewares.NewAuthMiddleware(tokenGen, logger),
		serviceAuthMid: serviceAuthMid,
		rabbitConn:     rabbitConn,
	}, nil
}

func (app *application) GetRabbitConn() *amqp.Connection {
	return app.rabbitConn
}

func (app *application) IsRabbitMQConnected() bool {
	return app.rabbitConn != nil && !app.rabbitConn.IsClosed()
}

func (app *application) Mount() *chi.Mux {
	r := chi.NewRouter()

	// Global middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	// Replace old metrics middleware with OTel-based one
	otelMetricsMid := middlewares.NewOTelMetricsMiddleware(app.logger)
	r.Use(otelMetricsMid.Metrics)

	metricsService := metrics.NewMetricsService(app.store.Metrics)
	// Add metrics middleware globally
	metricsMid := middlewares.NewMetricsMiddleware(metricsService, app.logger)
	r.Use(metricsMid.Metrics)

	authService := auth.NewAuthService(app.tokenGen, app.store.Users, app.store.Tokens)

	authHandler := auth.NewAuthHandler(app.logger, authService)
	ingredientHandler := ingredients.NewIngredientHandler(app.logger, app.store.Ingredients)
	healthHandler := health.NewHealthHandler(app.logger)
	recipeHandler := recipes.NewRecipeHandler(app.logger, app.store.Recipes)

	// Mount metrics endpoint outside of your API routes
	r.Handle("/metrics", promhttp.Handler()) // This is where OpenTelemetry exposes its metrics

	r.Route("/api/v1", func(r chi.Router) {
		// Public routes
		r.Get("/health", healthHandler.HealthCheckHandler)
		r.Get("/ready", healthHandler.ReadinessCheckHandler)

		// Auth routes
		r.Post("/auth/login", authHandler.Login)
		r.Post("/auth/refresh", authHandler.Refresh)

		// Service to service routes - MOVED OUTSIDE authenticated group
		r.Group(func(r chi.Router) {
			app.logger.Info("Setting up internal API routes")
			r.Use(app.serviceAuthMid.AuthenticateService)
			app.logger.Info("Service auth middleware attached to internal routes")

			// Internal recipes endpoints for service communication
			r.Post("/internal/recipes", recipeHandler.Create)
			app.logger.Info("Internal routes configured",
				"paths", []string{
					"POST /api/v1/internal/recipes",
				})
		})

		// Protected routes
		r.Group(func(r chi.Router) {
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

				r.Get("/search", func(w http.ResponseWriter, r *http.Request) {
					// Simple example - publish search query to RabbitMQ
					query := r.URL.Query().Get("q")
					if query == "" {
						http.Error(w, "Missing search query", http.StatusBadRequest)
						return
					}

					// Log the RabbitMQ URL
					app.logger.Infof("RABBITMQ_URL: %s", app.config.RabbitMQ.URL)

					ch, err := app.rabbitConn.Channel()
					if err != nil {
						app.logger.Error("Failed to open RabbitMQ channel", zap.Error(err))
						http.Error(w, "Internal server error", http.StatusInternalServerError)
						return
					}
					defer ch.Close()
					app.logger.Info("Connected to RabbitMQ successfully")

					workflowCommand := recipes.WorkflowCommand{
						WorkflowType: "recipe_workflow_full",
						WorkflowPayload: recipes.WorkflowPayload{
							SearchQuery:     query,
							ExcludedDomains: []string{},
							NumberOfUrls:    5,
						},
					}
					messageBodyBytes, err := json.Marshal(workflowCommand)
					if err != nil {
						app.logger.Error("Failed to marshal message body to JSON", zap.Error(err))
						http.Error(w, "Internal server error", http.StatusInternalServerError)
						return
					}
					messageBody := string(messageBodyBytes)

					ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
					defer cancel()
					routingKey := "workflow_messages"
					app.logger.Infof("Publishing message: exchange=%s, routingKey=%s, body=%s", "", routingKey, messageBody)
					err = ch.PublishWithContext(ctx,
						"",         // exchange
						routingKey, // routing key
						false,      // mandatory
						false,      // immediate
						amqp.Publishing{
							ContentType: "application/json",
							Body:        []byte(messageBody),
						})
					if err != nil {
						app.logger.Error("Failed to publish message", zap.Error(err))
						http.Error(w, "Internal server error", http.StatusInternalServerError)
						return
					}

					if err := ch.Close(); err != nil {
						app.logger.Error("Error closing channel", zap.Error(err))
					}

					app.logger.Info("Message published successfully")

					app.logger.Info(" [x] Sent %s\n", messageBody)

					w.WriteHeader(http.StatusAccepted)
					w.Write([]byte("Search request received"))
				})

				// Admin only routes
				r.Group(func(r chi.Router) {
					r.Use(app.authMid.RequireRole("admin"))
					r.Get("/urlsBySearchQuery", recipeHandler.FindUrlsBySearchQuery)
					r.Get("/{id}", recipeHandler.GetByID)
				})
			})

			// Logout (requires auth)
			r.Post("/auth/logout", authHandler.Logout)
			r.Post("/auth/logout/all", authHandler.LogoutAll)
		})
	})

	return r
}
