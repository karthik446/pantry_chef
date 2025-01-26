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

	"github.com/karthik446/pantry_chef/api/internal/platform/config"
	"github.com/karthik446/pantry_chef/api/internal/platform/db/postgres"
	server "github.com/karthik446/pantry_chef/api/internal/server/grpc"
	httpServer "github.com/karthik446/pantry_chef/api/internal/server/http"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
	"google.golang.org/grpc/reflection"
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
	db, err := postgres.New(postgres.Config{
		URL:          cfg.DB.Addr,
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
	app := httpServer.NewApplication(store, sugar)
	httpHandler := app.Mount()

	// Setup HTTP server
	httpServer := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Addr),
		Handler:      httpHandler,
		IdleTimeout:  time.Minute,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// Setup gRPC server
	grpcServer := server.NewGRPCServer()
	reflection.Register(grpcServer)

	// Setup gRPC listener
	grpcListener, err := net.Listen("tcp", ":9090")
	if err != nil {
		logger.Fatal("Failed to listen for gRPC",
			zap.Error(err),
		)
	}

	// Setup signal handling
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	// Start servers
	go func() {
		logger.Info("Starting HTTP server",
			zap.String("addr", cfg.Addr),
		)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("HTTP server failed",
				zap.Error(err),
			)
		}
	}()

	go func() {
		logger.Info("Starting gRPC server",
			zap.String("addr", ":9090"),
		)
		if err := grpcServer.Serve(grpcListener); err != nil {
			logger.Fatal("gRPC server failed",
				zap.Error(err),
			)
		}
	}()

	// Wait for interrupt signal
	<-quit
	logger.Info("Shutting down servers...")

	// Graceful shutdown
	grpcServer.GracefulStop()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := httpServer.Shutdown(ctx); err != nil {
		logger.Error("HTTP server shutdown error",
			zap.Error(err),
		)
	}
}
