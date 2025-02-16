package middlewares

import (
	"context"
	"net/http"
	"strings"

	"github.com/karthik446/pantry_chef/api/internal/platform/token"
	"go.uber.org/zap"
)

type AuthMiddleware struct {
	tokenGen token.Generator
	logger   *zap.SugaredLogger
}

func NewAuthMiddleware(tokenGen token.Generator, logger *zap.SugaredLogger) *AuthMiddleware {
	return &AuthMiddleware{tokenGen: tokenGen, logger: logger}
}

func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tokenString := extractToken(r)
		if tokenString == "" {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		claims, err := m.tokenGen.ValidateAccessToken(tokenString)
		if err != nil {
			m.logger.Error("Invalid token", "error", err)
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		// Add claims to context
		ctx := context.WithValue(r.Context(), "user_id", claims.UserID)
		ctx = context.WithValue(ctx, "user_number", claims.UserNumber)
		ctx = context.WithValue(ctx, "role", claims.Role)

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func (m *AuthMiddleware) RequireRole(role string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			userRole, ok := r.Context().Value("role").(string)
			if !ok || userRole == "" {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			if userRole != role {
				http.Error(w, "Forbidden", http.StatusForbidden)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func extractToken(r *http.Request) string {
	bearerToken := r.Header.Get("Authorization")
	if len(strings.Split(bearerToken, " ")) == 2 {
		return strings.Split(bearerToken, " ")[1]
	}
	return ""
}
