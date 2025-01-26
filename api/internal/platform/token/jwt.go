package token

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type JWTGenerator struct {
	config Config
}

func NewJWTGenerator(config Config) Generator {
	return &JWTGenerator{
		config: config,
	}
}

func (g *JWTGenerator) GenerateAccessToken(userID uuid.UUID, userNumber, role string) (string, error) {
	now := time.Now()
	claims := Claims{
		UserID:     userID,
		UserNumber: userNumber,
		Role:       role,
		TokenID:    uuid.New().String(),
		IssuedAt:   now.Unix(),
		ExpiresAt:  now.Add(g.config.AccessTokenDuration).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(g.config.SigningKey)
}

func (g *JWTGenerator) ValidateAccessToken(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, ErrInvalidToken
		}
		return g.config.SigningKey, nil
	})

	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*Claims); ok && token.Valid {
		return claims, nil
	}

	return nil, ErrInvalidToken
}

func (g *JWTGenerator) GenerateRefreshToken() (string, string, error) {
	// Generate a random 32-byte refresh token
	refreshBytes := make([]byte, 32)
	if _, err := rand.Read(refreshBytes); err != nil {
		return "", "", fmt.Errorf("failed to generate refresh token: %w", err)
	}

	// Convert to base64url for the actual token
	refreshToken := base64.RawURLEncoding.EncodeToString(refreshBytes)

	// Hash the token for storage
	hash := g.HashToken(refreshToken)

	return refreshToken, hash, nil
}

func (g *JWTGenerator) HashToken(token string) string {
	// Use SHA-256 for hashing the refresh token
	h := sha256.New()
	h.Write([]byte(token))
	return base64.RawURLEncoding.EncodeToString(h.Sum(nil))
}
