package auth

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

func NewAuthHandler(logger *zap.SugaredLogger, authService AuthServiceInterface) *AuthHandler {
	return &AuthHandler{
		BaseHandler: handlers.NewBaseHandler(logger),
		authService: authService,
	}
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	// Create new context with required values
	ctx := r.Context()
	ctx = context.WithValue(ctx, contextKeyUserAgent, r.UserAgent())
	ctx = context.WithValue(ctx, contextKeyClientIP, r.RemoteAddr)

	h.Logger.Infow("login attempt",
		"user_number", req.UserNumber,
		"user_agent", r.UserAgent(),
		"client_ip", r.RemoteAddr)

	resp, err := h.authService.Login(ctx, req.UserNumber.String(), req.Password)
	if err != nil {
		switch err {
		case ErrInvalidCredentials:
			h.Logger.Warnw("invalid credentials",
				"user_number", req.UserNumber,
				"error", err)
			h.UnauthorizedResponse(w, r)
		case store.ErrNotFound:
			h.Logger.Warnw("user not found",
				"user_number", req.UserNumber)
			h.UnauthorizedResponse(w, r)
		default:
			h.Logger.Errorw("login failed",
				"user_number", req.UserNumber,
				"error", err)
			h.InternalServerError(w, r, err)
		}
		return
	}

	h.Logger.Infow("login successful",
		"user_number", req.UserNumber)
	h.JsonResponse(w, http.StatusOK, envelope{"data": resp})
}

func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	var req refreshRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	ctx := r.Context()
	ctx = context.WithValue(ctx, contextKeyUserAgent, r.UserAgent())
	ctx = context.WithValue(ctx, contextKeyClientIP, r.RemoteAddr)

	resp, err := h.authService.RefreshToken(ctx, req.RefreshToken)
	if err != nil {
		h.UnauthorizedResponse(w, r)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": resp})
}

func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	token := h.extractRefreshToken(r)
	if token == "" {
		h.BadRequestResponse(w, r, nil)
		return
	}

	if err := h.authService.Logout(r.Context(), token); err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]string{
		"message": "logged out successfully",
	}})
}

func (h *AuthHandler) LogoutAll(w http.ResponseWriter, r *http.Request) {
	userID, ok := r.Context().Value("user_id").(uuid.UUID)
	if !ok {
		h.BadRequestResponse(w, r, nil)
		return
	}

	if err := h.authService.LogoutAll(r.Context(), userID); err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]string{
		"message": "logged out from all devices",
	}})
}

// Helper methods
func (h *AuthHandler) extractRefreshToken(r *http.Request) string {
	bearerToken := r.Header.Get("Authorization")
	if len(strings.Split(bearerToken, " ")) == 2 {
		return strings.Split(bearerToken, " ")[1]
	}
	return ""
}
