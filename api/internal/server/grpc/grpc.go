package server

import (
	"context"

	"github.com/karthik446/pantry_chef/api/internal/server/middleware"
	pb "github.com/karthik446/pantry_chef/api/proto"
	"google.golang.org/grpc"
)

type healthServer struct {
	pb.UnimplementedHealthServiceServer
}

func NewGRPCServer() *grpc.Server {
	server := grpc.NewServer(
		grpc.ChainUnaryInterceptor(
			middleware.UnaryServerInterceptor(),
			middleware.RecoveryInterceptor(),
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
