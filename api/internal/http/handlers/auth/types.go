package auth

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers"
)

type envelope map[string]interface{}

type AuthServiceInterface interface {
	Login(ctx context.Context, userNumber, password string) (*LoginResponse, error)
	Logout(ctx context.Context, refreshToken string) error
	LogoutAll(ctx context.Context, userID uuid.UUID) error
	RefreshToken(ctx context.Context, refreshToken string) (*LoginResponse, error)
}

type AuthHandler struct {
	handlers.BaseHandler
	authService AuthServiceInterface
}

type loginRequest struct {
	UserNumber json.Number `json:"user_number"`
	Password   string      `json:"password"`
}

type refreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}
type contextKey string

const (
	contextKeyUserAgent contextKey = "user_agent"
	contextKeyClientIP  contextKey = "client_ip"
)

// Define interfaces for what AuthService needs

type LoginResponse struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	ExpiresAt    time.Time `json:"expires_at"`
}
