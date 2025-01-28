package store

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type MetricsStore struct {
	db    *pgxpool.Pool
	mutex sync.RWMutex
}

type HTTPMetrics struct {
	ID             string           `json:"id"`
	RequestID      string           `json:"request_id"`
	Path           string           `json:"path"`
	Method         string           `json:"method"`
	RequestsTotal  int64            `json:"requests_total"`
	ResponseStatus map[string]int64 `json:"response_status"`
	ResponseSize   int64            `json:"response_size"`
	Duration       float64          `json:"duration"`
	CreatedAt      time.Time        `json:"created_at"`
}

type AuthMetrics struct {
	AttemptsTotal int64
	SuccessTotal  int64
	FailuresTotal int64
	LastUpdated   time.Time
}

type MetricsQuery struct {
	StartDate time.Time
	EndDate   time.Time
}

func NewMetricsStore(db *pgxpool.Pool) *MetricsStore {
	return &MetricsStore{
		db: db,
	}
}

func (s *MetricsStore) RecordHTTPMetric(ctx context.Context, requestID, path, method string, status int, size int64, duration time.Duration) error {
	statusMap := map[string]int64{
		fmt.Sprintf("%d", status): 1,
	}
	statusJSON, err := json.Marshal(statusMap)
	if err != nil {
		return err
	}

	query := `
		INSERT INTO http_metrics (
			request_id, path, method, response_status, 
			response_size, duration, date
		) VALUES ($1, $2, $3, $4, $5, $6, CURRENT_DATE)`

	_, err = s.db.Exec(ctx, query,
		requestID,
		path,
		method,
		statusJSON,
		size,
		duration.Seconds())
	return err
}

func (s *MetricsStore) RecordAuthMetric(ctx context.Context, metric AuthMetrics) error {
	query := `
		INSERT INTO auth_metrics (attempts_total, success_total, failures_total, date)
		VALUES ($1, $2, $3, CURRENT_DATE)
		ON CONFLICT (date) DO UPDATE SET
			attempts_total = auth_metrics.attempts_total + $1,
			success_total = auth_metrics.success_total + $2,
			failures_total = auth_metrics.failures_total + $3,
			last_updated = NOW()`

	_, err := s.db.Exec(ctx, query,
		metric.AttemptsTotal,
		metric.SuccessTotal,
		metric.FailuresTotal)
	return err
}

func (s *MetricsStore) GetMetrics(ctx context.Context, query MetricsQuery) (*MetricsResponse, error) {
	response := &MetricsResponse{
		HTTP: make(map[string][]HTTPMetrics),
		Auth: make(map[string]AuthMetrics),
	}

	httpQuery := `
		SELECT id, request_id, path, method, 
			   response_status::text,
			   response_size,
			   duration,
			   created_at,
			   date
		FROM http_metrics
		WHERE date BETWEEN $1 AND $2
		ORDER BY created_at DESC`

	rows, err := s.db.Query(ctx, httpQuery, query.StartDate, query.EndDate)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var m HTTPMetrics
		var date time.Time
		var statusJSON string
		err := rows.Scan(
			&m.ID,
			&m.RequestID,
			&m.Path,
			&m.Method,
			&statusJSON,
			&m.ResponseSize,
			&m.Duration,
			&m.CreatedAt,
			&date,
		)
		if err != nil {
			return nil, err
		}

		m.ResponseStatus = make(map[string]int64)
		if err := json.Unmarshal([]byte(statusJSON), &m.ResponseStatus); err != nil {
			return nil, err
		}

		dateKey := date.Format("2006-01-02")
		response.HTTP[dateKey] = append(response.HTTP[dateKey], m)
	}

	// Get Auth metrics with date range
	authQuery := `
		SELECT date,
			   SUM(attempts_total) as attempts_total,
			   SUM(success_total) as success_total,
			   SUM(failures_total) as failures_total
		FROM auth_metrics
		WHERE date BETWEEN $1 AND $2
		GROUP BY date
		ORDER BY date DESC`

	rows, err = s.db.Query(ctx, authQuery, query.StartDate, query.EndDate)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var m AuthMetrics
		var date time.Time
		err := rows.Scan(&date, &m.AttemptsTotal, &m.SuccessTotal, &m.FailuresTotal)
		if err != nil {
			return nil, err
		}
		dateKey := date.Format("2006-01-02")
		response.Auth[dateKey] = m
	}

	return response, nil
}

type MetricsResponse struct {
	HTTP map[string][]HTTPMetrics `json:"http"`
	Auth map[string]AuthMetrics   `json:"auth"`
}
