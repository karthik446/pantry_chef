package server

import (
	"context"

	"github.com/karthik446/pantry_chef/api/internal/server/middleware"
	pb "github.com/karthik446/pantry_chef/api/proto"
	"go.uber.org/zap"
	"google.golang.org/grpc"
)

type healthServer struct {
	pb.UnimplementedHealthServiceServer
}

func NewGRPCServer(logger *zap.SugaredLogger) *grpc.Server {
	server := grpc.NewServer(
		grpc.ChainUnaryInterceptor(
			middleware.UnaryServerInterceptor(logger),
			middleware.RecoveryInterceptor(logger),
		),
	)
	pb.RegisterHealthServiceServer(server, &healthServer{})
	return server
}

func (s *healthServer) Check(ctx context.Context, req *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{
		Status: pb.HealthCheckResponse_SERVING,
	}, nil
}
