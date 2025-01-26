package server

import (
	"net/http"
)

func (app *application) internalServerError(w http.ResponseWriter, r *http.Request, err error) {
	app.logger.Infow("internal-server-error", "path", r.URL.Path, "method", r.Method, "err", err)
	writeJSONError(w, http.StatusInternalServerError, "internal server error")
}

func (app *application) badRequestResponse(w http.ResponseWriter, r *http.Request, err error) {
	app.logger.Infow("bad-request-error ", "path", r.URL.Path, "method", r.Method, "err", err)
	writeJSONError(w, http.StatusBadRequest, err.Error())
}

func (app *application) notFoundResponse(w http.ResponseWriter, r *http.Request, err error) {
	app.logger.Infow("not-found-error", "path", r.URL.Path, "method", r.Method, "err", err)

	writeJSONError(w, http.StatusNotFound, err.Error())
}

func (app *application) invalidAuthenticationTokenResponse(w http.ResponseWriter, r *http.Request) {
	app.errorResponse(w, r, http.StatusUnauthorized, "invalid or missing authentication token")
}

func (app *application) authenticationRequiredResponse(w http.ResponseWriter, r *http.Request) {
	app.errorResponse(w, r, http.StatusUnauthorized, "you must be authenticated to access this resource")
}

func (app *application) notPermittedResponse(w http.ResponseWriter, r *http.Request) {
	app.errorResponse(w, r, http.StatusForbidden, "you don't have permission to access this resource")
}

func (app *application) errorResponse(w http.ResponseWriter, r *http.Request, status int, message string) {
	env := envelope{"error": message}
	app.jsonResponse(w, status, env)
}

func (app *application) unauthorizedResponse(w http.ResponseWriter, r *http.Request) {
	message := "unauthorized"
	app.errorResponse(w, r, http.StatusUnauthorized, message)
}

func (app *application) forbiddenResponse(w http.ResponseWriter, r *http.Request) {
	message := "forbidden"
	app.errorResponse(w, r, http.StatusForbidden, message)
}

type envelope map[string]interface{}

// func (app *application) duplicateKeyConflict(w http.ResponseWriter, r *http.Request, err error) {
// 	app.logger.Infow("duplicate-key-conflict", "path", r.URL.Path, "method", r.Method, "err", err)

// 	writeJSONError(w, http.StatusConflict, err.Error())
// }
