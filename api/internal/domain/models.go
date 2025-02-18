package domain

import (
	"time"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

type Ingredient struct {
	ID        uuid.UUID `json:"id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
}

type User struct {
	ID           uuid.UUID `json:"id"`
	UserNumber   string    `json:"user_number"`
	PasswordHash string    `json:"-"`
	CreatedAt    time.Time `json:"created_at"`
	IsActive     bool      `json:"is_active"`
	Role         string    `json:"role"`
}

func (u *User) VerifyPassword(password string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password))
	return err == nil
}

// Helper function to hash passwords
func HashPassword(password string) (string, error) {
	hashedBytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}
	return string(hashedBytes), nil
}

type UserPreferences struct {
	ID         uuid.UUID `json:"id"`
	UserID     uuid.UUID `json:"user_id"`
	SpiceLevel int       `json:"spice_level" binding:"min=1,max=5"`
}

type PantryItem struct {
	ID           uuid.UUID  `json:"id"`
	UserID       uuid.UUID  `json:"user_id"`
	IngredientID uuid.UUID  `json:"ingredient_id"`
	Quantity     float64    `json:"quantity"`
	Unit         string     `json:"unit"`
	ExpiryDate   *time.Time `json:"expiry_date,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
	Ingredient   *struct {
		Name string `json:"name"`
	} `json:"ingredients,omitempty"`
}

type Recipe struct {
	ID               uuid.UUID    `json:"id"`
	Title            string       `json:"title"`
	Instructions     string       `json:"instructions"`
	PrepTime         *int         `json:"prep_time,omitempty"`
	CookTime         *int         `json:"cook_time,omitempty"`
	TotalTime        *int         `json:"total_time,omitempty"`
	CreatedFromQuery *string      `json:"created_from_query,omitempty"`
	Servings         *int         `json:"servings,omitempty"`
	SourceURL        *string      `json:"source_url,omitempty"`
	CreatedAt        time.Time    `json:"created_at"`
	Ingredients      []Ingredient `json:"ingredients,omitempty"`
}

type RecipeIngredient struct {
	RecipeID     uuid.UUID `json:"recipe_id"`
	IngredientID uuid.UUID `json:"ingredient_id"`
	Quantity     float64   `json:"quantity"`
	Unit         string    `json:"unit"`
	Name         string    `json:"name,omitempty"` // For joined queries
}

type RecipeFilter struct {
	MaxTotalTime int
	Limit        int
	Offset       int
}
