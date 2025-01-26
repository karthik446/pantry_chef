package token

import (
	"errors"
	"time"

	"github.com/google/uuid"
)

var (
	ErrTokenExpired       = errors.New("token has expired")
	ErrTokenNotValidYet   = errors.New("token not valid yet")
	ErrInvalidToken       = errors.New("invalid token")
	ErrInvalidCredentials = errors.New("invalid credentials")
)

// Config holds token configuration
type Config struct {
	AccessTokenDuration  time.Duration
	RefreshTokenDuration time.Duration
	SigningKey           []byte
}

// Generator interface for token operations
type Generator interface {
	// GenerateAccessToken creates a new JWT access token
	GenerateAccessToken(userID uuid.UUID, userNumber, role string) (string, error)

	// GenerateRefreshToken creates a new refresh token
	GenerateRefreshToken() (string, string, error) // returns token, hash, error

	// ValidateAccessToken validates and returns claims from a JWT
	ValidateAccessToken(token string) (*Claims, error)

	// HashToken creates a hash of a refresh token for storage
	HashToken(token string) string
}
