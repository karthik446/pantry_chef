package dtos

type IngredientsDTO struct {
	IngredientName string
	Quantity       float64
	Unit           string
}

type CreateRecipeDTO struct {
	Title            string           `json:"title" validate:"required"`
	Instructions     string           `json:"instructions" validate:"required"`
	PrepTime         int              `json:"prep_time" validate:"required,gte=0"`
	CookTime         int              `json:"cook_time" validate:"required,gte=0"`
	TotalTime        int              `json:"total_time" validate:"required,gte=0"`
	Servings         int              `json:"servings" validate:"required,gt=0"`
	SourceURL        *string          `json:"source_url" validate:"omitempty,url"`
	CreatedFromQuery string           `json:"created_from_query,omitempty"`
	Ingredients      []IngredientsDTO `json:"ingredients" validate:"required,dive"`
	Notes            *string          `json:"notes,omitempty"`
}
