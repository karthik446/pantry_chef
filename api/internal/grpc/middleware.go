package grpc_server

import (
	"context"
	"time"

	"github.com/google/uuid"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/metric"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/peer"
)

// UnaryServerInterceptor logs requests for unary RPCs
func UnaryServerInterceptor(logger *zap.SugaredLogger) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		start := time.Now()
		requestID := uuid.New().String()

		// Add request ID to context
		ctx = metadata.AppendToOutgoingContext(ctx, "x-request-id", requestID)

		// Get peer info
		peer, _ := peer.FromContext(ctx)

		// Get meter
		meter := otel.GetMeterProvider().Meter("grpc-server")

		// Create metrics
		requestCounter, _ := meter.Int64Counter("grpc.requests.total")
		errorCounter, _ := meter.Int64Counter("grpc.errors.total")
		latencyHistogram, _ := meter.Float64Histogram("grpc.request.duration")

		// Process request
		resp, err := handler(ctx, req)

		// Record metrics
		duration := time.Since(start)
		requestCounter.Add(ctx, 1, metric.WithAttributes(
			attribute.String("method", info.FullMethod),
			attribute.String("peer", peer.Addr.String()),
		))

		latencyHistogram.Record(ctx, duration.Seconds(), metric.WithAttributes(
			attribute.String("method", info.FullMethod),
		))

		if err != nil {
			errorCounter.Add(ctx, 1, metric.WithAttributes(
				attribute.String("method", info.FullMethod),
				attribute.String("error", err.Error()),
			))
		}

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
func RecoveryInterceptor(logger *zap.SugaredLogger) grpc.UnaryServerInterceptor {
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
