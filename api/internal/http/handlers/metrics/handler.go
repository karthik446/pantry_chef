package metrics

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type MetricsHandler struct {
	service *MetricsService
	logger  *zap.SugaredLogger
}

func NewMetricsHandler(service *MetricsService, logger *zap.SugaredLogger) *MetricsHandler {
	return &MetricsHandler{
		service: service,
		logger:  logger,
	}
}

func formatDuration(d float64) string {
	switch {
	case d >= 1:
		return fmt.Sprintf("%.2fs", d)
	case d >= 0.001:
		return fmt.Sprintf("%.2fms", d*1000)
	default:
		return fmt.Sprintf("%.2fµs", d*1000000)
	}
}

type formattedMetricsResponse struct {
	HTTP map[string][]formattedHTTPMetrics `json:"http"`
	Auth map[string]store.AuthMetrics      `json:"auth"`
}

type formattedHTTPMetrics struct {
	Path           string           `json:"path"`
	Method         string           `json:"method"`
	RequestsTotal  int64            `json:"requests_total"`
	ResponseStatus map[string]int64 `json:"response_status"`
	ResponseSize   int64            `json:"response_size"`
	Duration       string           `json:"duration"`
	Requests       []RequestDetail  `json:"requests"`
}

type RequestDetail struct {
	RequestID string    `json:"request_id"`
	Status    int       `json:"status"`
	Size      int64     `json:"size"`
	Duration  string    `json:"duration"`
	CreatedAt time.Time `json:"created_at"`
}

func (h *MetricsHandler) GetMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	// Parse date range from query params
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")

	var query store.MetricsQuery
	if startDate == "" && endDate == "" {
		// If no dates specified, get all metrics
		query = store.MetricsQuery{
			StartDate: time.Time{}, // Zero time
			EndDate:   time.Now(),
		}
	} else {
		// Default to last 7 days if only partial dates provided
		query = store.MetricsQuery{
			StartDate: time.Now().AddDate(0, 0, -7),
			EndDate:   time.Now(),
		}

		if startDate != "" {
			if parsed, err := time.Parse("2006-01-02", startDate); err == nil {
				query.StartDate = parsed
			}
		}
		if endDate != "" {
			if parsed, err := time.Parse("2006-01-02", endDate); err == nil {
				query.EndDate = parsed
			}
		}
	}

	metrics, err := h.service.GetMetrics(r.Context(), query)
	if err != nil {
		h.logger.Error("Failed to fetch metrics", "error", err)
		http.Error(w, "Failed to fetch metrics", http.StatusInternalServerError)
		return
	}

	// Group metrics by date, path, and method
	formatted := formattedMetricsResponse{
		HTTP: make(map[string][]formattedHTTPMetrics),
		Auth: metrics.Auth,
	}

	// Group metrics
	groupedMetrics := make(map[string]map[string][]store.HTTPMetrics)
	for date, metrics := range metrics.HTTP {
		if groupedMetrics[date] == nil {
			groupedMetrics[date] = make(map[string][]store.HTTPMetrics)
		}
		for _, m := range metrics {
			key := fmt.Sprintf("%s:%s", m.Path, m.Method)
			groupedMetrics[date][key] = append(groupedMetrics[date][key], m)
		}
	}

	// Format grouped metrics
	for date, groups := range groupedMetrics {
		for _, metrics := range groups {
			if len(metrics) == 0 {
				continue
			}

			// Use first metric for common fields
			first := metrics[0]
			totalRequests := int64(len(metrics))
			totalSize := int64(0)
			totalDuration := float64(0)
			statusCounts := make(map[string]int64)
			requests := make([]RequestDetail, 0, len(metrics))

			// Calculate totals
			for _, m := range metrics {
				totalSize += m.ResponseSize
				totalDuration += m.Duration
				for status, count := range m.ResponseStatus {
					statusCounts[status] += count
				}

				// Add request detail
				status := 0
				for s, _ := range m.ResponseStatus {
					status, _ = strconv.Atoi(s)
					break
				}
				requests = append(requests, RequestDetail{
					RequestID: m.RequestID,
					Status:    status,
					Size:      m.ResponseSize,
					Duration:  formatDuration(m.Duration),
					CreatedAt: m.CreatedAt,
				})
			}

			avgDuration := totalDuration / float64(len(metrics))

			formatted.HTTP[date] = append(formatted.HTTP[date], formattedHTTPMetrics{
				Path:           first.Path,
				Method:         first.Method,
				RequestsTotal:  totalRequests,
				ResponseStatus: statusCounts,
				ResponseSize:   totalSize,
				Duration:       formatDuration(avgDuration),
				Requests:       requests,
			})
		}
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(formatted); err != nil {
		http.Error(w, "Failed to encode metrics", http.StatusInternalServerError)
		return
	}
}
