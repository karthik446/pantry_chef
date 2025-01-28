package middlewares

import (
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5/middleware"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/metrics"
	"go.uber.org/zap"
)

type MetricsMiddleware struct {
	service *metrics.MetricsService
	logger  *zap.SugaredLogger
}

type statusRecorder struct {
	http.ResponseWriter
	status int
	size   int64
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	size, err := r.ResponseWriter.Write(b)
	r.size += int64(size)
	return size, err
}

func NewMetricsMiddleware(service *metrics.MetricsService, logger *zap.SugaredLogger) *MetricsMiddleware {
	return &MetricsMiddleware{service: service, logger: logger}
}

func (m *MetricsMiddleware) Metrics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Get request ID from context (set by chi's middleware.RequestID)
		requestID := middleware.GetReqID(r.Context())
		if requestID == "" {
			m.logger.Warn("Request ID not found in context")
			requestID = "unknown"
		}

		recorder := &statusRecorder{
			ResponseWriter: w,
			status:         http.StatusOK,
		}

		// Call next handler
		next.ServeHTTP(recorder, r)

		duration := time.Since(start)

		// Record HTTP metrics
		if err := m.service.RecordHTTPMetric(
			r.Context(),
			requestID,
			r.URL.Path,
			r.Method,
			recorder.status,
			recorder.size,
			duration,
		); err != nil {
			// Log error but don't fail the request
			m.logger.Error("Failed to record HTTP metrics", "error", err)
		}

		// Record Auth metrics if applicable
		if strings.HasPrefix(r.URL.Path, "/api/v1/auth") {
			if err := m.service.RecordAuthMetric(
				r.Context(),
				recorder.status == http.StatusOK,
			); err != nil {
				// Log error but don't fail the request
				m.logger.Error("Failed to record Auth metrics", "error", err)
			}
		}
	})
}
