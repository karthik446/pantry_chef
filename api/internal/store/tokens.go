package store

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrTokenNotFound = errors.New("refresh token not found")
	ErrTokenRevoked  = errors.New("refresh token has been revoked")
	ErrTokenExpired  = errors.New("refresh token has expired")
)

type RefreshToken struct {
	ID              uuid.UUID
	UserID          uuid.UUID
	TokenHash       string
	ExpiresAt       time.Time
	CreatedAt       time.Time
	RevokedAt       *time.Time
	ReplacedByToken *string
	UserAgent       string
	ClientIP        string
}

func (t *RefreshToken) IsExpired() bool {
	return time.Now().After(t.ExpiresAt)
}

func (t *RefreshToken) IsRevoked() bool {
	return t.RevokedAt != nil
}

type TokenStore struct {
	db *pgxpool.Pool
}

func NewTokenStore(db *pgxpool.Pool) *TokenStore {
	return &TokenStore{db: db}
}

func (s *TokenStore) CreateRefreshToken(ctx context.Context, token RefreshToken) error {
	query := `
		INSERT INTO refresh_tokens (
			user_id, token_hash, expires_at, user_agent, client_ip
		) VALUES ($1, $2, $3, $4, $5)
		RETURNING id, created_at`

	return s.db.QueryRow(
		ctx,
		query,
		token.UserID,
		token.TokenHash,
		token.ExpiresAt,
		token.UserAgent,
		token.ClientIP,
	).Scan(&token.ID, &token.CreatedAt)
}

func (s *TokenStore) GetRefreshToken(ctx context.Context, tokenHash string) (*RefreshToken, error) {
	query := `
		SELECT id, user_id, token_hash, expires_at, created_at, 
		       revoked_at, replaced_by_token, user_agent, client_ip
		FROM refresh_tokens
		WHERE token_hash = $1`

	var token RefreshToken
	err := s.db.QueryRow(ctx, query, tokenHash).Scan(
		&token.ID,
		&token.UserID,
		&token.TokenHash,
		&token.ExpiresAt,
		&token.CreatedAt,
		&token.RevokedAt,
		&token.ReplacedByToken,
		&token.UserAgent,
		&token.ClientIP,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTokenNotFound
		}
		return nil, err
	}

	return &token, nil
}

func (s *TokenStore) RevokeRefreshToken(ctx context.Context, tokenHash string) error {
	query := `
		UPDATE refresh_tokens
		SET revoked_at = NOW()
		WHERE token_hash = $1 AND revoked_at IS NULL`

	tag, err := s.db.Exec(ctx, query, tokenHash)
	if err != nil {
		return err
	}

	if tag.RowsAffected() == 0 {
		return ErrTokenNotFound
	}

	return nil
}

func (s *TokenStore) RevokeAllUserTokens(ctx context.Context, userID uuid.UUID) error {
	query := `
		UPDATE refresh_tokens
		SET revoked_at = NOW()
		WHERE user_id = $1 AND revoked_at IS NULL`

	_, err := s.db.Exec(ctx, query, userID)
	return err
}

func (s *TokenStore) RotateRefreshToken(ctx context.Context, oldTokenHash string, newToken RefreshToken) error {
	tx, err := s.db.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	// Revoke old token
	query := `
		UPDATE refresh_tokens
		SET revoked_at = NOW(), replaced_by_token = $1
		WHERE token_hash = $2 AND revoked_at IS NULL
		RETURNING id`

	var oldTokenID string
	err = tx.QueryRow(ctx, query, newToken.TokenHash, oldTokenHash).Scan(&oldTokenID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ErrTokenNotFound
		}
		return err
	}

	// Create new token
	query = `
		INSERT INTO refresh_tokens (
			user_id, token_hash, expires_at, user_agent, client_ip
		) VALUES ($1, $2, $3, $4, $5)
		RETURNING id, created_at`

	err = tx.QueryRow(
		ctx,
		query,
		newToken.UserID,
		newToken.TokenHash,
		newToken.ExpiresAt,
		newToken.UserAgent,
		newToken.ClientIP,
	).Scan(&newToken.ID, &newToken.CreatedAt)
	if err != nil {
		return err
	}

	return tx.Commit(ctx)
}
