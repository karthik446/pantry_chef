package store

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/karthik446/pantry_chef/api/internal/domain"
)

var (
	ErrNotFound             = errors.New("resource not found")
	ErrDuplicateKeyConflict = errors.New("duplicate key value violates unique constraint")
	QueryTimeOutDuration    = time.Second * 5
)

type UserStoreInterface interface {
	GetUserByNumber(ctx context.Context, userNumber string) (*domain.User, error)
	GetUser(ctx context.Context, id uuid.UUID) (*domain.User, error)
}

type TokenStoreInterface interface {
	CreateRefreshToken(ctx context.Context, token RefreshToken) error
	GetRefreshToken(ctx context.Context, tokenHash string) (*RefreshToken, error)
	RevokeRefreshToken(ctx context.Context, tokenHash string) error
	RevokeAllUserTokens(ctx context.Context, userID uuid.UUID) error
	RotateRefreshToken(ctx context.Context, oldTokenHash string, newToken RefreshToken) error
}

type IngredientStoreInterface interface {
	Create(ctx context.Context, dto *domain.CreateIngredientDTO) (*domain.Ingredient, error)
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Ingredient, error)
	List(ctx context.Context) ([]domain.Ingredient, int, error)
	Update(ctx context.Context, id uuid.UUID, dto *domain.CreateIngredientDTO) error
	Delete(ctx context.Context, id uuid.UUID) error
}

type Storage struct {
	Ingredients IngredientStoreInterface
	Tokens      TokenStoreInterface
	Users       UserStoreInterface
}

func NewStorage(db *pgxpool.Pool) *Storage {
	return &Storage{
		Ingredients: &IngredientsStore{db: db},
		Tokens:      &TokenStore{db: db},
		Users:       &UserStore{db: db},
	}
}
