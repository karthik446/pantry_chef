package server

import (
	"encoding/json"
	"errors"
	"net/http"

	"github.com/karthik446/pantry_chef/api/internal/domain"
	"github.com/karthik446/pantry_chef/api/internal/store"
)

func (app *application) listIngredientsHandler(w http.ResponseWriter, r *http.Request) {
	ingredients, count, err := app.store.Ingredients.List(r.Context())
	if err != nil {
		app.internalServerError(w, r, err)
		return
	}

	app.jsonResponse(w, http.StatusOK, map[string]interface{}{
		"data":  ingredients,
		"count": count,
	})
}

func (app *application) createIngredientHandler(w http.ResponseWriter, r *http.Request) {
	var dto domain.CreateIngredientDTO

	err := json.NewDecoder(r.Body).Decode(&dto)
	if err != nil {
		app.badRequestResponse(w, r, err)
		return
	}

	ingredient, err := app.store.Ingredients.Create(r.Context(), &dto)
	if err != nil {
		app.internalServerError(w, r, err)
		return
	}

	app.jsonResponse(w, http.StatusCreated, ingredient)
}

func (app *application) updateIngredientHandler(w http.ResponseWriter, r *http.Request) {
	ingredient := r.Context().Value("ingredient").(*domain.Ingredient)

	var dto domain.CreateIngredientDTO
	err := json.NewDecoder(r.Body).Decode(&dto)
	if err != nil {
		app.badRequestResponse(w, r, err)
		return
	}

	err = app.store.Ingredients.Update(r.Context(), ingredient.ID, &dto)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrNotFound):
			app.notFoundResponse(w, r, err)
		default:
			app.internalServerError(w, r, err)
		}
		return
	}

	app.jsonResponse(w, http.StatusOK, map[string]string{
		"message": "ingredient updated successfully",
	})
}

func (app *application) deleteIngredientHandler(w http.ResponseWriter, r *http.Request) {
	ingredient := r.Context().Value("ingredient").(*domain.Ingredient)

	err := app.store.Ingredients.Delete(r.Context(), ingredient.ID)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrNotFound):
			app.notFoundResponse(w, r, err)
		default:
			app.internalServerError(w, r, err)
		}
		return
	}

	app.jsonResponse(w, http.StatusOK, map[string]string{
		"message": "ingredient deleted successfully",
	})
}
