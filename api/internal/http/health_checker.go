package http_server

import (
	"sync"
	"time"
)

type HealthStatus string

const (
	StatusUp   HealthStatus = "UP"
	StatusDown HealthStatus = "DOWN"
)

type Component struct {
	Name   string       `json:"name"`
	Status HealthStatus `json:"status"`
}

type Health struct {
	mu         sync.RWMutex
	Status     HealthStatus            `json:"status"`
	Components map[string]HealthStatus `json:"components"`
	Uptime     time.Time               `json:"uptime"`
}

func NewHealthChecker() *Health {
	return &Health{
		Status:     StatusUp,
		Components: make(map[string]HealthStatus),
		Uptime:     time.Now(),
	}
}

func (h *Health) RegisterComponent(name string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.Components[name] = StatusUp
}

func (h *Health) SetComponentStatus(name string, status HealthStatus) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.Components[name] = status
	h.updateOverallStatus()
}

func (h *Health) updateOverallStatus() {
	for _, status := range h.Components {
		if status == StatusDown {
			h.Status = StatusDown
			return
		}
	}
	h.Status = StatusUp
}

func (h *Health) HealthStatus() map[string]interface{} {
	h.mu.RLock()
	defer h.mu.RUnlock()

	return map[string]interface{}{
		"status":     h.Status,
		"components": h.Components,
		"uptime":     time.Since(h.Uptime).String(),
	}
}

func (h *Health) IsHealthy() bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.Status == StatusUp
}
