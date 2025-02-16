package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/karthik446/pantry_chef/api/internal/domain"
	"github.com/karthik446/pantry_chef/api/internal/http/dtos"
)

type RecipeStore struct {
	db *pgxpool.Pool
}

// CreateRecipeDTO represents the data needed to create a recipe

func (s *RecipeStore) Create(ctx context.Context, dto *dtos.CreateRecipeDTO) (*domain.Recipe, error) {
	tx, err := s.db.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	recipe := &domain.Recipe{}

	// Insert recipe
	err = tx.QueryRow(
		ctx,
		`INSERT INTO recipes (
			title, instructions, prep_time, cook_time, total_time,
			servings, source_url, created_from_search_query
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id, created_at`,
		dto.Title,
		dto.Instructions,
		dto.PrepTime,
		dto.CookTime,
		dto.TotalTime,
		dto.Servings,
		dto.SourceURL,
		dto.CreatedFromQuery,
	).Scan(&recipe.ID, &recipe.CreatedAt)

	if err != nil {
		return nil, err
	}

	// Process ingredients
	for _, ing := range dto.Ingredients {
		ingredientID, err := s.findOrCreateIngredient(ctx, tx, ing.IngredientName)
		if err != nil {
			return nil, err
		}

		_, err = tx.Exec(
			ctx,
			`INSERT INTO recipe_ingredients (
				recipe_id, ingredient_id, quantity, unit
			) VALUES ($1, $2, $3, $4)`,
			recipe.ID,
			ingredientID,
			ing.Quantity,
			ing.Unit,
		)
		if err != nil {
			return nil, err
		}
	}

	if err = tx.Commit(ctx); err != nil {
		return nil, err
	}

	// Fetch complete recipe with ingredients
	return s.GetByID(ctx, recipe.ID)
}

func (s *RecipeStore) FindUrlsBySearchQuery(ctx context.Context, query string) ([]string, error) {
	// Split search query into words and filter out short words
	words := strings.Split(strings.ToLower(query), " ")
	searchWords := make([]string, 0)
	for _, word := range words {
		if len(word) > 2 {
			searchWords = append(searchWords, word)
		}
	}

	if len(searchWords) == 0 {
		return []string{}, nil
	}

	// Query recipes with non-null source_url and created_from_search_query
	rows, err := s.db.Query(ctx,
		`SELECT source_url, created_from_search_query 
		FROM recipes 
		WHERE source_url IS NOT NULL 
		AND created_from_search_query IS NOT NULL`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var urls []string
	for rows.Next() {
		var sourceURL string
		var createdFromQuery string
		if err := rows.Scan(&sourceURL, &createdFromQuery); err != nil {
			return nil, err
		}

		// Check if at least 2 search words match
		existingWords := strings.Split(strings.ToLower(createdFromQuery), " ")
		matches := 0
		for _, searchWord := range searchWords {
			for _, existingWord := range existingWords {
				if strings.Contains(existingWord, searchWord) {
					matches++
					break
				}
			}
		}

		if matches >= 2 {
			urls = append(urls, sourceURL)
		}
	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return urls, nil

}

func (s *RecipeStore) GetByID(ctx context.Context, id uuid.UUID) (*domain.Recipe, error) {
	recipe := &domain.Recipe{}

	// Get recipe details
	err := s.db.QueryRow(
		ctx,
		`SELECT 
			id, title, instructions, prep_time, cook_time, total_time,
			servings, source_url, created_from_search_query, created_at
		FROM recipes WHERE id = $1`,
		id,
	).Scan(
		&recipe.ID,
		&recipe.Title,
		&recipe.Instructions,
		&recipe.PrepTime,
		&recipe.CookTime,
		&recipe.TotalTime,
		&recipe.Servings,
		&recipe.SourceURL,
		&recipe.CreatedFromQuery,
		&recipe.CreatedAt,
	)

	if err == sql.ErrNoRows {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	// Get recipe ingredients
	rows, err := s.db.Query(
		ctx,
		`SELECT 
			i.id, i.name, ri.quantity, ri.unit
		FROM recipe_ingredients ri
		JOIN ingredients i ON i.id = ri.ingredient_id
		WHERE ri.recipe_id = $1`,
		recipe.ID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var ing domain.Ingredient
		err := rows.Scan(
			&ing.ID,
			&ing.Name,
		)
		if err != nil {
			return nil, err
		}
		recipe.Ingredients = append(recipe.Ingredients, ing)
	}

	return recipe, nil
}

func (s *RecipeStore) List(ctx context.Context, filter domain.RecipeFilter) ([]domain.Recipe, int, error) {
	// Base query
	query := `
		SELECT 
			id, title, instructions, prep_time, cook_time, total_time,
			servings, source_url, created_from_search_query, created_at
		FROM recipes
		WHERE 1=1`

	countQuery := `SELECT COUNT(*) FROM recipes WHERE 1=1`
	args := []interface{}{}

	// Apply filters
	if filter.MaxTotalTime > 0 {
		query += fmt.Sprintf(" AND total_time <= $%d", len(args)+1)
		countQuery += fmt.Sprintf(" AND total_time <= $%d", len(args)+1)
		args = append(args, filter.MaxTotalTime)
	}

	// Add ordering
	query += ` ORDER BY created_at DESC`

	// Add pagination
	if filter.Limit > 0 {
		query += fmt.Sprintf(" LIMIT $%d", len(args)+1)
		args = append(args, filter.Limit)

		if filter.Offset > 0 {
			query += fmt.Sprintf(" OFFSET $%d", len(args)+1)
			args = append(args, filter.Offset)
		}
	}

	// Get total count
	var total int
	err := s.db.QueryRow(ctx, countQuery, args...).Scan(&total)
	if err != nil {
		return nil, 0, err
	}

	// Get recipes
	rows, err := s.db.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var recipes []domain.Recipe
	for rows.Next() {
		var r domain.Recipe
		err := rows.Scan(
			&r.ID,
			&r.Title,
			&r.Instructions,
			&r.PrepTime,
			&r.CookTime,
			&r.TotalTime,
			&r.Servings,
			&r.SourceURL,
			&r.CreatedFromQuery,
			&r.CreatedAt,
		)
		if err != nil {
			return nil, 0, err
		}
		recipes = append(recipes, r)
	}

	return recipes, total, nil
}

// findOrCreateIngredient attempts to find a matching ingredient or creates a new one
// TODO: Implement proper ingredient matching logic
func (s *RecipeStore) findOrCreateIngredient(ctx context.Context, tx pgx.Tx, name string) (uuid.UUID, error) {
	var id uuid.UUID

	// First try to find exact match
	err := tx.QueryRow(
		ctx,
		"SELECT id FROM ingredients WHERE name = $1",
		name,
	).Scan(&id)

	if err == nil {
		return id, nil
	}

	if !errors.Is(err, sql.ErrNoRows) {
		return uuid.Nil, err
	}

	// TODO: Implement fuzzy matching logic here
	// For now, create new ingredient
	err = tx.QueryRow(
		ctx,
		"INSERT INTO ingredients (name) VALUES ($1) RETURNING id",
		name,
	).Scan(&id)

	if err != nil {
		return uuid.Nil, err
	}

	return id, nil
}
