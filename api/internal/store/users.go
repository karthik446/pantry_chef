package store

import (
	"context"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/karthik446/pantry_chef/api/internal/domain"
)

type UserStore struct {
	db *pgxpool.Pool
}

func NewUserStore(db *pgxpool.Pool) *UserStore {
	return &UserStore{db: db}
}

func (s *UserStore) GetUserByNumber(ctx context.Context, userNumber string) (*domain.User, error) {
	query := `
		SELECT id, user_number, password_hash, created_at, is_active, role
		FROM users
		WHERE user_number = $1::text`

	var user domain.User
	err := s.db.QueryRow(ctx, query, userNumber).Scan(
		&user.ID,
		&user.UserNumber,
		&user.PasswordHash,
		&user.CreatedAt,
		&user.IsActive,
		&user.Role,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, err
	}

	return &user, nil
}

func (s *UserStore) GetUser(ctx context.Context, id uuid.UUID) (*domain.User, error) {
	query := `
		SELECT id, user_number, password_hash, created_at, is_active, role
		FROM users
		WHERE id = $1`

	var user domain.User
	err := s.db.QueryRow(ctx, query, id).Scan(
		&user.ID,
		&user.UserNumber,
		&user.PasswordHash,
		&user.CreatedAt,
		&user.IsActive,
		&user.Role,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, err
	}

	return &user, nil
}
