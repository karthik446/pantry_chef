package ingredients

import (
	"encoding/json"
	"errors"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/http/dtos"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type IngredientHandler struct {
	handlers.BaseHandler
	store store.IngredientStoreInterface
}

type envelope map[string]interface{}

func NewIngredientHandler(logger *zap.SugaredLogger, store store.IngredientStoreInterface) *IngredientHandler {
	return &IngredientHandler{
		BaseHandler: handlers.NewBaseHandler(logger),
		store:       store,
	}
}

func (h *IngredientHandler) List(w http.ResponseWriter, r *http.Request) {
	ingredients, count, err := h.store.List(r.Context())
	if err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]interface{}{
		"ingredients": ingredients,
		"count":       count,
	}})
}

func (h *IngredientHandler) Create(w http.ResponseWriter, r *http.Request) {
	var dto dtos.CreateIngredientDTO

	err := json.NewDecoder(r.Body).Decode(&dto)
	if err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	ingredient, err := h.store.Create(r.Context(), &dto)
	if err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusCreated, envelope{"data": ingredient})
}

func (h *IngredientHandler) Update(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	ingredientID, err := uuid.Parse(id)
	if err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	var dto dtos.CreateIngredientDTO
	err = json.NewDecoder(r.Body).Decode(&dto)
	if err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	err = h.store.Update(r.Context(), ingredientID, &dto)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrNotFound):
			h.NotFoundResponse(w, r, err)
		default:
			h.InternalServerError(w, r, err)
		}
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]string{
		"message": "ingredient updated successfully",
	}})
}

func (h *IngredientHandler) Delete(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	ingredientID, err := uuid.Parse(id)
	if err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	err = h.store.Delete(r.Context(), ingredientID)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrNotFound):
			h.NotFoundResponse(w, r, err)
		default:
			h.InternalServerError(w, r, err)
		}
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]string{
		"message": "ingredient deleted successfully",
	}})
}
