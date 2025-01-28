package dtos

type IngredientDTO struct {
	Name     string  `json:"name" binding:"required"`
	Quantity float64 `json:"quantity" binding:"required"`
	Unit     string  `json:"unit" binding:"required"`
}

type CreateIngredientDTO struct {
	Name string `json:"name" binding:"required"`
}
