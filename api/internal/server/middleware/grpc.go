package middleware

import (
	"context"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/peer"

	logger "github.com/karthik446/pantry_chef/api/internal/platform/logger"
	metrics "github.com/karthik446/pantry_chef/api/internal/platform/metrics"
)

// UnaryServerInterceptor logs requests for unary RPCs
func UnaryServerInterceptor() grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		start := time.Now()
		requestID := uuid.New().String()

		// Add request ID to context
		ctx = metadata.AppendToOutgoingContext(ctx, "x-request-id", requestID)

		// Get peer info
		peer, _ := peer.FromContext(ctx)

		// Process request
		resp, err := handler(ctx, req)

		duration := time.Since(start)
		status := "success"
		if err != nil {
			status = "error"
			metrics.GRPCErrorsTotal.Inc()
		}

		// Record metrics
		metrics.GRPCRequestsTotal.WithLabelValues(status).Inc()

		// Log request details
		logger.Info("gRPC Request",
			zap.String("request_id", requestID),
			zap.String("method", info.FullMethod),
			zap.Duration("duration", duration),
			zap.String("peer_address", peer.Addr.String()),
			zap.Error(err),
		)

		return resp, err
	}
}

// RecoveryInterceptor handles panics in gRPC handlers
func RecoveryInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (resp interface{}, err error) {
		defer func() {
			if r := recover(); r != nil {
				md, _ := metadata.FromIncomingContext(ctx)
				requestID := md.Get("x-request-id")[0]

				logger.Error("Panic recovered in gRPC handler",
					zap.Any("panic", r),
					zap.String("request_id", requestID),
					zap.String("method", info.FullMethod),
				)
				err = grpc.Errorf(codes.Internal, "Internal server error")
			}
		}()

		return handler(ctx, req)
	}
}
