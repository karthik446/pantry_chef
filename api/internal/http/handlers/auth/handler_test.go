package auth

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"go.uber.org/zap"
)

type MockAuthService struct {
	mock.Mock
}

func (m *MockAuthService) Login(ctx context.Context, userNumber, password string) (*LoginResponse, error) {
	args := m.Called(ctx, userNumber, password)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*LoginResponse), args.Error(1)
}

func (m *MockAuthService) Logout(ctx context.Context, refreshToken string) error {
	args := m.Called(ctx, refreshToken)
	return args.Error(0)
}

func (m *MockAuthService) LogoutAll(ctx context.Context, userID uuid.UUID) error {
	args := m.Called(ctx, userID)
	return args.Error(0)
}

func (m *MockAuthService) RefreshToken(ctx context.Context, refreshToken string) (*LoginResponse, error) {
	args := m.Called(ctx, refreshToken)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*LoginResponse), args.Error(1)
}

// Implement AuthServiceInterface methods...
// (same as your current mock implementation)

func TestLogin(t *testing.T) {
	tests := []struct {
		name           string
		requestBody    interface{}
		setupMock      func(*MockAuthService)
		expectedStatus int
		expectedBody   string
	}{
		{
			name: "successful login",
			requestBody: loginRequest{
				UserNumber: json.Number("1234567890"),
				Password:   "password123",
			},
			setupMock: func(mas *MockAuthService) {
				expiresAt := time.Date(2025, 1, 26, 12, 51, 50, 705496000, time.Local)
				mas.On("Login", mock.Anything, "1234567890", "password123").Return(
					&LoginResponse{
						AccessToken:  "test-access-token",
						RefreshToken: "test-refresh-token",
						ExpiresAt:    expiresAt,
					}, nil)
			},
			expectedStatus: http.StatusOK,
			expectedBody: `{
				"data": {
					"access_token": "test-access-token",
					"refresh_token": "test-refresh-token",
					"expires_at": "2025-01-26T12:51:50.705496-07:00"
				}
			}`,
		},
		{
			name: "invalid credentials",
			requestBody: loginRequest{
				UserNumber: json.Number("1234567890"),
				Password:   "wrongpass",
			},
			setupMock: func(mas *MockAuthService) {
				mas.On("Login", mock.Anything, "1234567890", "wrongpass").Return(
					nil, ErrInvalidCredentials)
			},
			expectedStatus: http.StatusUnauthorized,
			expectedBody: `{
				"data": {
					"error": "unauthorized"
				}
			}`,
		},
		{
			name: "invalid request body",
			requestBody: map[string]interface{}{
				"user_number": "invalid",
				"password":    123, // wrong type
			},
			setupMock: func(mas *MockAuthService) {
				// No mock setup needed as handler should fail before service call
			},
			expectedStatus: http.StatusBadRequest,
			expectedBody: `{
				"data": {
					"error": "bad request"
				}
			}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create mock service
			mockAuthService := new(MockAuthService)
			tt.setupMock(mockAuthService)

			// Create handler with mocked service
			handler := NewAuthHandler(zap.NewNop().Sugar(), mockAuthService)

			// Create request
			body, _ := json.Marshal(tt.requestBody)
			req := httptest.NewRequest(http.MethodPost, "/v1/auth/login", bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			// Create response recorder
			rr := httptest.NewRecorder()

			// Call handler
			handler.Login(rr, req)

			// Assert response
			assert.Equal(t, tt.expectedStatus, rr.Code)

			var expected, actual map[string]interface{}
			json.Unmarshal([]byte(tt.expectedBody), &expected)
			json.Unmarshal(rr.Body.Bytes(), &actual)
			assert.Equal(t, expected, actual)

			mockAuthService.AssertExpectations(t)
		})
	}
}
