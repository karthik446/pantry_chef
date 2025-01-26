package handlers

import (
	"encoding/json"
	"net/http"

	"go.uber.org/zap"
)

type BaseHandler struct {
	Logger *zap.SugaredLogger
}

type envelope map[string]interface{}

func NewBaseHandler(logger *zap.SugaredLogger) BaseHandler {
	return BaseHandler{
		Logger: logger,
	}
}

func (h *BaseHandler) JsonResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func (h *BaseHandler) BadRequestResponse(w http.ResponseWriter, r *http.Request, err error) {
	h.JsonResponse(w, http.StatusBadRequest, envelope{"data": envelope{
		"error": "bad request",
	}})
}

func (h *BaseHandler) UnauthorizedResponse(w http.ResponseWriter, r *http.Request) {
	h.JsonResponse(w, http.StatusUnauthorized, envelope{"data": envelope{
		"error": "unauthorized",
	}})
}

func (h *BaseHandler) NotFoundResponse(w http.ResponseWriter, r *http.Request, err error) {
	h.JsonResponse(w, http.StatusNotFound, envelope{"data": envelope{
		"error": "not found",
	}})
}

func (h *BaseHandler) InternalServerError(w http.ResponseWriter, r *http.Request, err error) {
	h.Logger.Errorw("internal server error", "error", err)
	h.JsonResponse(w, http.StatusInternalServerError, envelope{"data": envelope{
		"error": "internal server error",
	}})
}
