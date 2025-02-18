package recipes

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/karthik446/pantry_chef/api/internal/domain"
	"github.com/karthik446/pantry_chef/api/internal/http/dtos"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers"
	"github.com/karthik446/pantry_chef/api/internal/http/handlers/auth"
	"github.com/karthik446/pantry_chef/api/internal/store"
	"go.uber.org/zap"
)

type RecipeHandler struct {
	handlers.BaseHandler
	store store.RecipeStoreInterface
}

type envelope map[string]interface{}

type WorkflowPayload struct {
	SearchQuery     string   `json:"search_query"`
	ExcludedDomains []string `json:"excluded_domains"`
	NumberOfUrls    int      `json:"number_of_urls"`
}

type WorkflowCommand struct {
	WorkflowType    string          `json:"workflow_type"`
	WorkflowPayload WorkflowPayload `json:"workflow_payload"`
}

func NewRecipeHandler(logger *zap.SugaredLogger, store store.RecipeStoreInterface) *RecipeHandler {
	return &RecipeHandler{
		BaseHandler: handlers.NewBaseHandler(logger),
		store:       store,
	}
}

func (h *RecipeHandler) List(w http.ResponseWriter, r *http.Request) {
	var filter domain.RecipeFilter

	// Parse query parameters
	if maxTime := r.URL.Query().Get("max_time"); maxTime != "" {
		if mt, err := strconv.Atoi(maxTime); err == nil {
			filter.MaxTotalTime = mt
		}
	}

	// Parse pagination
	if limit := r.URL.Query().Get("limit"); limit != "" {
		if l, err := strconv.Atoi(limit); err == nil {
			filter.Limit = l
		}
	}
	if offset := r.URL.Query().Get("offset"); offset != "" {
		if o, err := strconv.Atoi(offset); err == nil {
			filter.Offset = o
		}
	}

	recipes, count, err := h.store.List(r.Context(), filter)
	if err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": map[string]interface{}{
		"recipes": recipes,
		"count":   count,
	}})
}

func (h *RecipeHandler) Create(w http.ResponseWriter, r *http.Request) {
	h.Logger.Info("Creating recipe, details: ", r.Body)
	var dto dtos.CreateRecipeDTO

	// Add debug logging
	isService, ok := r.Context().Value(auth.ContextKeyIsService).(bool)
	h.Logger.Info("Context values",
		"isService", isService,
		"ok", ok,
		"contextKeys", fmt.Sprintf("%v", r.Context()))

	if !isService {
		http.Error(w, "Unauthorized: Service access only", http.StatusForbidden)
		return
	}

	err := json.NewDecoder(r.Body).Decode(&dto)
	h.Logger.Info("Decoded dto Ingredients: ", dto.Ingredients)
	if err != nil {
		h.Logger.Error("Error decoding dto: ", err)
		h.BadRequestResponse(w, r, err)
		return
	}

	recipe, err := h.store.Create(r.Context(), &dto)
	h.Logger.Info("Created recipe: ", recipe)
	if err != nil {
		h.Logger.Error("Error creating recipe: ", err)
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusCreated, envelope{"data": recipe})
}

func (h *RecipeHandler) GetByID(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	recipeID, err := uuid.Parse(id)
	if err != nil {
		h.BadRequestResponse(w, r, err)
		return
	}

	recipe, err := h.store.GetByID(r.Context(), recipeID)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrNotFound):
			h.NotFoundResponse(w, r, err)
		default:
			h.InternalServerError(w, r, err)
		}
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": recipe})
}

func (h *RecipeHandler) FindUrlsBySearchQuery(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query().Get("query")
	urls, err := h.store.FindUrlsBySearchQuery(r.Context(), query)
	if err != nil {
		h.InternalServerError(w, r, err)
		return
	}

	h.JsonResponse(w, http.StatusOK, envelope{"data": urls})
}
