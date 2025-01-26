package auth

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const (
	UserContextKey contextKey = "user"
)

type JWTClaims struct {
	jwt.RegisteredClaims        // This embeds all required methods
	Email                string `json:"email"`
	Role                 string `json:"role"`
}

func AuthMiddleware(supabaseKey string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				http.Error(w, "No authorization header", http.StatusUnauthorized)
				return
			}

			// Extract Bearer token
			tokenString := strings.TrimPrefix(authHeader, "Bearer ")
			if tokenString == authHeader {
				http.Error(w, "Invalid authorization header format", http.StatusUnauthorized)
				return
			}

			// Parse and validate JWT
			token, err := jwt.ParseWithClaims(tokenString, &JWTClaims{}, func(token *jwt.Token) (interface{}, error) {
				if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
				}
				return []byte(supabaseKey), nil
			})

			if err != nil {
				http.Error(w, "Invalid token", http.StatusUnauthorized)
				return
			}

			claims, ok := token.Claims.(*JWTClaims)
			if !ok || !token.Valid {
				http.Error(w, "Invalid token claims", http.StatusUnauthorized)
				return
			}

			// Create user context
			user := &SupabaseUser{
				ID:    claims.Subject,
				Email: claims.Email,
				Role:  claims.Role,
			}

			// Add user to context
			ctx := context.WithValue(r.Context(), UserContextKey, user)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// Helper to get user from context
func GetUser(ctx context.Context) (*SupabaseUser, error) {
	user, ok := ctx.Value(UserContextKey).(*SupabaseUser)
	if !ok {
		return nil, fmt.Errorf("no user in context")
	}
	return user, nil
}

// Helper to check if user is admin
func IsAdmin(ctx context.Context) bool {
	user, err := GetUser(ctx)
	if err != nil {
		return false
	}
	return user.Role == "admin"
}
