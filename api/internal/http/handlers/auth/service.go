package auth

import (
	"context"
	"errors"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/platform/token"

	"github.com/karthik446/pantry_chef/api/internal/store"
)

type AuthService struct {
	tokenGen token.Generator
	users    store.UserStoreInterface
	tokens   store.TokenStoreInterface
}

func NewAuthService(tokenGen token.Generator, users store.UserStoreInterface, tokens store.TokenStoreInterface) *AuthService {
	return &AuthService{
		tokenGen: tokenGen,
		users:    users,
		tokens:   tokens,
	}
}

var (
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrInvalidToken       = errors.New("invalid token")
)

func (s *AuthService) Login(ctx context.Context, userNumber, password string) (*LoginResponse, error) {
	// Debug logging
	userAgent := ctx.Value(contextKeyUserAgent)
	clientIP := ctx.Value(contextKeyClientIP)

	log.Printf("Debug - Context values: userAgent=%v, clientIP=%v", userAgent, clientIP)

	// Verify credentials
	user, err := s.users.GetUserByNumber(ctx, userNumber)
	if err != nil {
		return nil, err
	}

	if !user.VerifyPassword(password) {
		return nil, ErrInvalidCredentials
	}

	// Generate tokens
	accessToken, err := s.tokenGen.GenerateAccessToken(user.ID, user.UserNumber, string(user.Role))
	if err != nil {
		return nil, err
	}

	refreshToken, hash, err := s.tokenGen.GenerateRefreshToken()
	if err != nil {
		return nil, err
	}

	// Add nil checks for context values
	var ua, ip string
	if v := ctx.Value(contextKeyUserAgent); v != nil {
		ua = v.(string)
	}
	if v := ctx.Value(contextKeyClientIP); v != nil {
		ip = v.(string)
	}

	// Store refresh token
	err = s.tokens.CreateRefreshToken(ctx, store.RefreshToken{
		UserID:    user.ID,
		TokenHash: hash,
		ExpiresAt: time.Now().Add(7 * 24 * time.Hour),
		UserAgent: ua,
		ClientIP:  ip,
	})
	if err != nil {
		return nil, err
	}

	return &LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresAt:    time.Now().Add(15 * time.Minute),
	}, nil
}

func (s *AuthService) RefreshToken(ctx context.Context, refreshToken string) (*LoginResponse, error) {
	// Verify refresh token
	hash := s.tokenGen.HashToken(refreshToken)
	storedToken, err := s.tokens.GetRefreshToken(ctx, hash)
	if err != nil {
		return nil, err
	}

	if storedToken.IsExpired() || storedToken.IsRevoked() {
		return nil, ErrInvalidToken
	}

	// Get user
	user, err := s.users.GetUser(ctx, storedToken.UserID)
	if err != nil {
		return nil, err
	}

	// Generate new tokens
	accessToken, err := s.tokenGen.GenerateAccessToken(user.ID, user.UserNumber, string(user.Role))
	if err != nil {
		return nil, err
	}

	newRefreshToken, newHash, err := s.tokenGen.GenerateRefreshToken()
	if err != nil {
		return nil, err
	}

	var ua, ip string
	if v := ctx.Value(contextKeyUserAgent); v != nil {
		ua = v.(string)
	}
	if v := ctx.Value(contextKeyClientIP); v != nil {
		ip = v.(string)
	}
	// Rotate refresh token
	err = s.tokens.RotateRefreshToken(ctx, hash, store.RefreshToken{
		UserID:    user.ID,
		TokenHash: newHash,
		ExpiresAt: time.Now().Add(7 * 24 * time.Hour),
		UserAgent: ua,
		ClientIP:  ip,
	})
	if err != nil {
		return nil, err
	}

	return &LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: newRefreshToken,
		ExpiresAt:    time.Now().Add(15 * time.Minute),
	}, nil
}

func (s *AuthService) Logout(ctx context.Context, refreshToken string) error {
	hash := s.tokenGen.HashToken(refreshToken)
	return s.tokens.RevokeRefreshToken(ctx, hash)
}

func (s *AuthService) LogoutAll(ctx context.Context, userID uuid.UUID) error {
	return s.tokens.RevokeAllUserTokens(ctx, userID)
}
