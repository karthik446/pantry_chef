package metrics

import (
	"context"
	"time"

	"github.com/karthik446/pantry_chef/api/internal/store"
)

type MetricsService struct {
	store store.MetricsStoreInterface
}

func NewMetricsService(store store.MetricsStoreInterface) *MetricsService {
	return &MetricsService{
		store: store,
	}
}

func (s *MetricsService) RecordHTTPMetric(ctx context.Context, requestID, path, method string, status int, size int64, duration time.Duration) error {

	return s.store.RecordHTTPMetric(ctx, requestID, path, method, status, size, duration)
}

func (s *MetricsService) RecordAuthMetric(ctx context.Context, success bool) error {
	metric := store.AuthMetrics{
		AttemptsTotal: 1,
		SuccessTotal: func() int64 {
			if success {
				return 1
			}
			return 0
		}(),
		FailuresTotal: func() int64 {
			if !success {
				return 1
			}
			return 0
		}(),
		LastUpdated: time.Now(),
	}

	return s.store.RecordAuthMetric(ctx, metric)
}

func (s *MetricsService) GetMetrics(ctx context.Context, query store.MetricsQuery) (*store.MetricsResponse, error) {
	return s.store.GetMetrics(ctx, query)
}
