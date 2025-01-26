package store

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	models "github.com/karthik446/pantry_chef/api/internal/domain"
)

var (
	ErrNotFound             = errors.New("resource not found")
	ErrDuplicateKeyConflict = errors.New("duplicate key value violates unique constraint")
	QueryTimeOutDuration    = time.Second * 5
)

type Storage struct {
	Ingredients interface {
		Create(ctx context.Context, dto *models.CreateIngredientDTO) (*models.Ingredient, error)
		GetByID(ctx context.Context, id uuid.UUID) (*models.Ingredient, error)
		List(ctx context.Context) ([]models.Ingredient, int, error)
		Update(ctx context.Context, id uuid.UUID, dto *models.CreateIngredientDTO) error
		Delete(ctx context.Context, id uuid.UUID) error
	}
}

func NewStorage(db *pgxpool.Pool) *Storage {
	return &Storage{
		Ingredients: &IngredientsStore{db: db},
	}
}
