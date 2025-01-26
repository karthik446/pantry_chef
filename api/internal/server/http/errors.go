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

// func (app *application) duplicateKeyConflict(w http.ResponseWriter, r *http.Request, err error) {
// 	app.logger.Infow("duplicate-key-conflict", "path", r.URL.Path, "method", r.Method, "err", err)

// 	writeJSONError(w, http.StatusConflict, err.Error())
// }
