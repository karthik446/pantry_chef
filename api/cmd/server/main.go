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

	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/db"
	httpServer "github.com/karthik446/pantry_chef/api/internal/server/http"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

func main() {
	// Initialize logger
	logger, err := zap.NewProduction()
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

	// Initialize database
	db, err := db.New(db.Config{
		URL:          cfg.DB.URL,
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

	// Initialize application
	app, err := httpServer.NewApplication(cfg, store, sugar)
	if err != nil {
		logger.Fatal("Failed to initialize application",
			zap.Error(err),
		)
	}
	httpHandler := app.Mount()

	// Setup HTTP server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Addr),
		Handler:      httpHandler,
		IdleTimeout:  time.Minute,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// Setup signal handling for graceful shutdown
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

	// Start server
	go func() {
		logger.Info("Starting server",
			zap.String("addr", cfg.Addr),
		)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server failed",
				zap.Error(err),
			)
		}
	}()

	// Wait for interrupt signal
	<-shutdown
	logger.Info("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("Server shutdown error",
			zap.Error(err),
		)
	}
}
