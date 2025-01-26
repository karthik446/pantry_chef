package server

import (
	"net/http"
)

var healthChecker = NewHealthChecker()

func init() {
	// Register components to health checker
	healthChecker.RegisterComponent("database")
	healthChecker.RegisterComponent("cache")
	healthChecker.RegisterComponent("grpc")
}

func (app *application) healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	if healthChecker.IsHealthy() {
		app.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"status":      "UP",
			"version":     app.config.Version,
			"environment": app.config.Env,
		})
		return
	}

	app.jsonResponse(w, http.StatusServiceUnavailable, map[string]interface{}{
		"status":      "DOWN",
		"components":  healthChecker.HealthStatus(),
		"version":     app.config.Version,
		"environment": app.config.Env,
	})
}

func (app *application) readinessCheckHandler(w http.ResponseWriter, r *http.Request) {
	app.jsonResponse(w, http.StatusOK, healthChecker.HealthStatus())
}
