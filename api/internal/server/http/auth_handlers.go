package server

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/server/service"
	"github.com/karthik446/pantry_chef/api/internal/store"
)

const (
	contextKeyUserAgent contextKey = "user_agent"
	contextKeyClientIP  contextKey = "client_ip"
)

type loginRequest struct {
	UserNumber json.Number `json:"user_number"`
	Password   string      `json:"password"`
}

type refreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}

func (app *application) loginHandler(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := readJSON(w, r, &req); err != nil {
		app.badRequestResponse(w, r, err)
		return
	}

	// Create new context with required values
	ctx := r.Context()
	ctx = context.WithValue(ctx, contextKeyUserAgent, r.UserAgent())
	ctx = context.WithValue(ctx, contextKeyClientIP, r.RemoteAddr)

	app.logger.Infow("login attempt",
		"user_number", req.UserNumber,
		"user_agent", r.UserAgent(),
		"client_ip", r.RemoteAddr)

	// Use the new context
	resp, err := app.authService.Login(ctx, req.UserNumber.String(), req.Password)
	if err != nil {
		switch err {
		case service.ErrInvalidCredentials:
			app.logger.Warnw("invalid credentials",
				"user_number", req.UserNumber,
				"error", err)
			app.unauthorizedResponse(w, r)
		case store.ErrNotFound:
			app.logger.Warnw("user not found",
				"user_number", req.UserNumber)
			app.unauthorizedResponse(w, r)
		default:
			app.logger.Errorw("login failed",
				"user_number", req.UserNumber,
				"error", err)
			app.internalServerError(w, r, err)
		}
		return
	}

	app.logger.Infow("login successful",
		"user_number", req.UserNumber)
	app.jsonResponse(w, http.StatusOK, resp)
}

func (app *application) refreshTokenHandler(w http.ResponseWriter, r *http.Request) {
	var req refreshRequest
	if err := readJSON(w, r, &req); err != nil {
		app.badRequestResponse(w, r, err)
		return
	}

	ctx := r.Context()
	ctx = context.WithValue(ctx, contextKeyUserAgent, r.UserAgent())
	ctx = context.WithValue(ctx, contextKeyClientIP, r.RemoteAddr)

	resp, err := app.authService.RefreshToken(ctx, req.RefreshToken)
	if err != nil {
		app.unauthorizedResponse(w, r)
		return
	}

	app.jsonResponse(w, http.StatusOK, resp)
}

func (app *application) logoutHandler(w http.ResponseWriter, r *http.Request) {
	token := extractRefreshToken(r)
	if token == "" {
		app.badRequestResponse(w, r, nil)
		return
	}

	if err := app.authService.Logout(r.Context(), token); err != nil {
		app.internalServerError(w, r, err)
		return
	}

	app.jsonResponse(w, http.StatusOK, map[string]string{
		"message": "logged out successfully",
	})
}

func (app *application) logoutAllHandler(w http.ResponseWriter, r *http.Request) {
	userID, ok := r.Context().Value("user_id").(uuid.UUID)
	if !ok {
		app.badRequestResponse(w, r, nil)
		return
	}

	if err := app.authService.LogoutAll(r.Context(), userID); err != nil {
		app.internalServerError(w, r, err)
		return
	}

	app.jsonResponse(w, http.StatusOK, map[string]string{
		"message": "logged out from all devices",
	})
}

// Helper function to extract refresh token from Authorization header
func extractRefreshToken(r *http.Request) string {
	bearerToken := r.Header.Get("Authorization")
	if len(strings.Split(bearerToken, " ")) == 2 {
		return strings.Split(bearerToken, " ")[1]
	}
	return ""
}
