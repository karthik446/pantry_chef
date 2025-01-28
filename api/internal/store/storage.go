package store

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/karthik446/pantry_chef/api/internal/domain"
	"github.com/karthik446/pantry_chef/api/internal/http/dtos"
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
	Create(ctx context.Context, dto *dtos.CreateIngredientDTO) (*domain.Ingredient, error)
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Ingredient, error)
	List(ctx context.Context) ([]domain.Ingredient, int, error)
	Update(ctx context.Context, id uuid.UUID, dto *dtos.CreateIngredientDTO) error
	Delete(ctx context.Context, id uuid.UUID) error
}

type MetricsStoreInterface interface {
	RecordHTTPMetric(ctx context.Context, requestID, path, method string, status int, size int64, duration time.Duration) error
	RecordAuthMetric(ctx context.Context, metric AuthMetrics) error
	GetMetrics(ctx context.Context, query MetricsQuery) (*MetricsResponse, error)
}

type RecipeStoreInterface interface {
	Create(ctx context.Context, dto *dtos.CreateRecipeDTO) (*domain.Recipe, error)
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Recipe, error)
	List(ctx context.Context, filter domain.RecipeFilter) ([]domain.Recipe, int, error)
	FindUrlsBySearchQuery(ctx context.Context, query string) ([]string, error)
}

type Storage struct {
	Ingredients IngredientStoreInterface
	Tokens      TokenStoreInterface
	Users       UserStoreInterface
	Metrics     MetricsStoreInterface
	Recipes     RecipeStoreInterface
}

func NewStorage(db *pgxpool.Pool) *Storage {
	return &Storage{
		Ingredients: &IngredientsStore{db: db},
		Tokens:      &TokenStore{db: db},
		Users:       &UserStore{db: db},
		Metrics:     &MetricsStore{db: db},
		Recipes:     &RecipeStore{db: db},
	}
}
