package token

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// Claims represents the claims in our JWT
type Claims struct {
	UserID     uuid.UUID `json:"user_id"`
	UserNumber string    `json:"user_number"`
	Role       string    `json:"role"`
	TokenID    string    `json:"token_id"`
	IssuedAt   int64     `json:"iat"`
	ExpiresAt  int64     `json:"exp"`
	jwt.RegisteredClaims
}

// Valid implements jwt.Claims interface
func (c Claims) Valid() error {
	now := time.Now().Unix()
	if now > c.ExpiresAt {
		return ErrTokenExpired
	}
	if now < c.IssuedAt {
		return ErrTokenNotValidYet
	}
	return nil
}

// Add these methods to implement jwt.Claims interface
func (c Claims) GetExpirationTime() (*jwt.NumericDate, error) {
	return jwt.NewNumericDate(time.Unix(c.ExpiresAt, 0)), nil
}

func (c Claims) GetIssuedAt() (*jwt.NumericDate, error) {
	return jwt.NewNumericDate(time.Unix(c.IssuedAt, 0)), nil
}

func (c Claims) GetNotBefore() (*jwt.NumericDate, error) {
	return nil, nil
}

func (c Claims) GetIssuer() (string, error) {
	return "", nil
}

func (c Claims) GetSubject() (string, error) {
	return "", nil
}

func (c Claims) GetAudience() (jwt.ClaimStrings, error) {
	return nil, nil
}
