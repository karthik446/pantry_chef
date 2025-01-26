package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	grpcServer "github.com/karthik446/pantry_chef/api/internal/grpc"
	httpServer "github.com/karthik446/pantry_chef/api/internal/http"
	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/db"
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

	// Initialize gRPC server
	grpcSrv := grpcServer.NewGRPCServer(sugar)
	grpcListener, err := net.Listen("tcp", fmt.Sprintf(":%s", cfg.GRPC.Port))
	if err != nil {
		logger.Fatal("Failed to create gRPC listener",
			zap.Error(err),
		)
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

	// Start gRPC server
	go func() {
		logger.Info("Starting gRPC server",
			zap.String("addr", cfg.GRPC.Port),
		)
		if err := grpcSrv.Serve(grpcListener); err != nil {
			logger.Fatal("gRPC server failed",
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

	// Stop gRPC server
	grpcSrv.GracefulStop()

	// Stop HTTP server
	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("Server shutdown error",
			zap.Error(err),
		)
	}
}
