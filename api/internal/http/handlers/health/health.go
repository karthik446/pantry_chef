package health

import (
	"net/http"

	"github.com/karthik446/pantry_chef/api/internal/http/handlers"
	"go.uber.org/zap"
)

var healthChecker = NewHealthChecker()

func init() {
	// Register components to health checker
	healthChecker.RegisterComponent("database")
	healthChecker.RegisterComponent("cache")
	healthChecker.RegisterComponent("grpc")
}

type healthHandler struct {
	handlers.BaseHandler
}

func NewHealthHandler(logger *zap.SugaredLogger) *healthHandler {
	return &healthHandler{
		BaseHandler: handlers.NewBaseHandler(logger),
	}
}

func (h *healthHandler) HealthCheckHandler(w http.ResponseWriter, _ *http.Request) {
	if healthChecker.IsHealthy() {
		h.JsonResponse(w, http.StatusOK, map[string]interface{}{
			"status": "UP",
		})
		return
	}

	h.JsonResponse(w, http.StatusServiceUnavailable, map[string]interface{}{
		"status":     "DOWN",
		"components": healthChecker.HealthStatus(),
	})
}

func (h *healthHandler) ReadinessCheckHandler(w http.ResponseWriter, _ *http.Request) {
	h.JsonResponse(w, http.StatusOK, healthChecker.HealthStatus())
}
