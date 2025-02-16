package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	httpServer "github.com/karthik446/pantry_chef/api/internal/http"
	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/db"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

func main() {
	// Initialize logger
	logConfig := zap.NewDevelopmentConfig()
	logConfig.Level = zap.NewAtomicLevelAt(zap.DebugLevel) // Set debug level
	logger, err := logConfig.Build()
	if err != nil {
		log.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Sync()
	sugar := logger.Sugar()

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("Failed to load config",
			zap.Error(err),
		)
	}

	// Add this before db.New
	sugar.Infof("Attempting to connect to database with URL: postgresql://%s:****@%s:%s/%s?sslmode=disable",
		cfg.DB.User, cfg.DB.Host, cfg.DB.Port, cfg.DB.DBName)

	// Initialize database
	dbURL := cfg.DB.GetURL()
	db, err := db.New(db.Config{
		URL:          dbURL,
		MaxOpenConns: int32(cfg.DB.MaxOpenConns),
		MaxIdleTime:  15 * time.Minute,
	})
	if err != nil {
		logger.Fatal("Failed to initialize database",
			zap.Error(err),
		)
	}
	defer db.Close()

	// Initialize store
	store := store.NewStorage(db)

	// Initialize HTTP application
	app, err := httpServer.NewApplication(cfg, store, sugar)
	if err != nil {
		logger.Fatal("Failed to initialize application",
			zap.Error(err),
		)
	}
	httpHandler := app.Mount()

	// Setup HTTP server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.HTTP.Port),
		Handler:      httpHandler,
		IdleTimeout:  time.Minute,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// Setup signal handling for graceful shutdown
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

	// Start HTTP server
	go func() {
		logger.Info("Starting HTTP server",
			zap.String("addr", cfg.HTTP.Port),
		)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("HTTP server failed",
				zap.Error(err),
			)
		}
	}()

	// Wait for interrupt signal
	<-shutdown
	logger.Info("Shutting down servers...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Stop HTTP server
	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("Server shutdown error",
			zap.Error(err),
		)
	}

	if app != nil && app.GetRabbitConn() != nil {
		if err := app.GetRabbitConn().Close(); err != nil {
			logger.Error("RabbitMQ connection close error", zap.Error(err))
		}
		logger.Info("RabbitMQ connection closed")
	}

	logger.Info("Server shutdown complete")
}
