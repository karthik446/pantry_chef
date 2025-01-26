package platform

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var registry = prometheus.NewRegistry()

var (
	// HTTP metrics
	HTTPRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests by status code",
		},
		[]string{"status_code"},
	)

	HTTPErrorsTotal = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "http_errors_total",
			Help: "Total number of HTTP errors (5xx responses)",
		},
	)

	// gRPC metrics
	GRPCRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "grpc_requests_total",
			Help: "Total number of gRPC requests by status",
		},
		[]string{"status"},
	)

	GRPCErrorsTotal = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "grpc_errors_total",
			Help: "Total number of gRPC errors",
		},
	)
)

func init() {
	// Register metrics with our custom registry
	registry.MustRegister(HTTPRequestsTotal)
	registry.MustRegister(HTTPErrorsTotal)
	registry.MustRegister(GRPCRequestsTotal)
	registry.MustRegister(GRPCErrorsTotal)
}

// Handler returns an HTTP handler for metrics
func Handler() http.Handler {
	return promhttp.HandlerFor(registry, promhttp.HandlerOpts{})
}
