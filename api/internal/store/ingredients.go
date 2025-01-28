package store

import (
	"context"
	"database/sql"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	models "github.com/karthik446/pantry_chef/api/internal/domain"
	"github.com/karthik446/pantry_chef/api/internal/http/dtos"
)

type IngredientsStore struct {
	db *pgxpool.Pool
}

func (s *IngredientsStore) Create(ctx context.Context, dto *dtos.CreateIngredientDTO) (*models.Ingredient, error) {
	result := &models.Ingredient{
		Name: dto.Name,
	}

	err := s.db.QueryRow(
		ctx,
		`INSERT INTO ingredients (name) VALUES ($1) RETURNING id, created_at`,
		dto.Name,
	).Scan(&result.ID, &result.CreatedAt)

	if err != nil {
		return nil, err
	}
	return result, nil
}

func (s *IngredientsStore) GetByID(ctx context.Context, id uuid.UUID) (*models.Ingredient, error) {
	ingredient := &models.Ingredient{}
	query := `
		SELECT id, name, created_at
		FROM ingredients
		WHERE id = $1`

	err := s.db.QueryRow(ctx, query, id).Scan(
		&ingredient.ID,
		&ingredient.Name,
		&ingredient.CreatedAt,
	)

	if err == sql.ErrNoRows {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return ingredient, nil
}

func (s *IngredientsStore) List(ctx context.Context) ([]models.Ingredient, int, error) {
	query := `
		SELECT id, name, created_at
		FROM ingredients`

	rows, err := s.db.Query(ctx, query)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var ingredients []models.Ingredient
	for rows.Next() {
		var i models.Ingredient
		err := rows.Scan(
			&i.ID,
			&i.Name,
			&i.CreatedAt,
		)
		if err != nil {
			return nil, 0, err
		}
		ingredients = append(ingredients, i)
	}

	if err = rows.Err(); err != nil {
		return nil, 0, err
	}

	var count int
	err = s.db.QueryRow(ctx, "SELECT COUNT(*) FROM ingredients").Scan(&count)
	if err != nil {
		return nil, 0, err
	}

	return ingredients, count, nil
}

func (s *IngredientsStore) Update(ctx context.Context, id uuid.UUID, dto *dtos.CreateIngredientDTO) error {
	query := `
		UPDATE ingredients
		SET name = $1
		WHERE id = $2`

	result, err := s.db.Exec(
		ctx,
		query,
		dto.Name,
		id,
	)
	if err != nil {
		return err
	}

	if result.RowsAffected() == 0 {
		return ErrNotFound
	}

	return nil
}

func (s *IngredientsStore) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM ingredients WHERE id = $1`

	result, err := s.db.Exec(ctx, query, id)
	if err != nil {
		return err
	}

	if result.RowsAffected() == 0 {
		return ErrNotFound
	}

	return nil
}
