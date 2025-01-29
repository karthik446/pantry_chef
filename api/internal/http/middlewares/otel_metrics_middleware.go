package middlewares

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"go.uber.org/zap"
)

type OTelMetricsMiddleware struct {
	logger *zap.SugaredLogger
	// Use Prometheus counters directly
	requestCounter   *prometheus.CounterVec
	errorCounter     *prometheus.CounterVec
	latencyHistogram *prometheus.HistogramVec
	authCounter      *prometheus.CounterVec
}

func NewOTelMetricsMiddleware(logger *zap.SugaredLogger) *OTelMetricsMiddleware {
	m := &OTelMetricsMiddleware{
		logger: logger,
		requestCounter: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "http_requests_total",
				Help: "Total number of HTTP requests",
			},
			[]string{"method", "path", "status"},
		),
		errorCounter: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "http_errors_total",
				Help: "Total number of HTTP errors",
			},
			[]string{"method", "path", "error_type"},
		),
		latencyHistogram: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "http_request_duration_seconds",
				Help:    "HTTP request duration in seconds",
				Buckets: prometheus.DefBuckets,
			},
			[]string{"method", "path"},
		),
		authCounter: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "auth_attempts_total",
				Help: "Total number of authentication attempts",
			},
			[]string{"success"},
		),
	}
	return m
}

func (m *OTelMetricsMiddleware) Metrics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		recorder := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		next.ServeHTTP(recorder, r)

		duration := time.Since(start)

		// Record request
		m.requestCounter.WithLabelValues(
			r.Method,
			r.URL.Path,
			strconv.Itoa(recorder.status),
		).Inc()

		// Record latency
		m.latencyHistogram.WithLabelValues(
			r.Method,
			r.URL.Path,
		).Observe(duration.Seconds())

		// Record errors
		if recorder.status >= 400 {
			errorType := strconv.Itoa(recorder.status/100) + "xx"
			m.errorCounter.WithLabelValues(
				r.Method,
				r.URL.Path,
				errorType,
			).Inc()
		}

		// Record auth attempts
		if r.URL.Path == "/api/v1/auth/login" {
			success := recorder.status == http.StatusOK
			m.authCounter.WithLabelValues(
				strconv.FormatBool(success),
			).Inc()
		}

		// Log request details
		m.logger.Infow("HTTP Request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", recorder.status,
			"duration", duration,
		)
	})
}

type OTelStatusRecorder struct {
	http.ResponseWriter
	status int
	size   int64
}

func (r *OTelStatusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func (r *OTelStatusRecorder) Write(b []byte) (int, error) {
	size, err := r.ResponseWriter.Write(b)
	r.size += int64(size)
	return size, err
}
