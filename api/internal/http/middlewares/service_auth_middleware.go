package middlewares

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/karthik446/pantry_chef/api/internal/http/handlers/auth"
	"go.uber.org/zap"
	authv1 "k8s.io/api/authentication/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type ServiceAuthMiddleware struct {
	logger    *zap.SugaredLogger
	k8sClient *kubernetes.Clientset
}

type K8sTokenReview struct {
	APIVersion string `json:"apiVersion"`
	Kind       string `json:"kind"`
	Status     struct {
		Authenticated bool `json:"authenticated"`
		User          struct {
			Username string   `json:"username"`
			Groups   []string `json:"groups"`
		} `json:"user"`
	} `json:"status"`
}

func NewServiceAuthMiddleware(logger *zap.SugaredLogger, k8sClient *kubernetes.Clientset) *ServiceAuthMiddleware {
	return &ServiceAuthMiddleware{logger: logger, k8sClient: k8sClient}
}

func (m *ServiceAuthMiddleware) AuthenticateService(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		m.logger.Info("=== Service Auth Middleware Start ===")
		m.logger.Info("Request details",
			"path", r.URL.Path,
			"method", r.Method,
			"remote_addr", r.RemoteAddr)

		// Log all headers for debugging
		for name, values := range r.Header {
			m.logger.Info("Header",
				"name", name,
				"values", values)
		}

		tokenString := extractServiceToken(r)
		if tokenString == "" {
			m.logger.Error("No service token provided",
				"authorization", r.Header.Get("Authorization"))
			http.Error(w, "Service token required", http.StatusUnauthorized)
			return
		}

		m.logger.Info("Token received",
			"token_length", len(tokenString),
			"token_preview", tokenString[:10]+"..."+tokenString[len(tokenString)-10:])

		// Verify token with Kubernetes TokenReview API
		authenticated, serviceAccount, err := m.verifyServiceToken(tokenString)
		if err != nil {
			m.logger.Error("Token verification failed",
				"error", err,
				"error_type", fmt.Sprintf("%T", err))
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		if !authenticated {
			m.logger.Error("Service not authenticated",
				"service_account", serviceAccount)
			http.Error(w, "Service not authorized", http.StatusUnauthorized)
			return
		}

		m.logger.Info("Service authenticated successfully",
			"service_account", serviceAccount)

		// Add service info to context
		ctx := context.WithValue(r.Context(), auth.ContextKeyServiceAccount, serviceAccount)
		ctx = context.WithValue(ctx, auth.ContextKeyIsService, true)

		m.logger.Info("=== Service Auth Middleware End ===")
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func extractServiceToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		return ""
	}

	return parts[1]
}

func (m *ServiceAuthMiddleware) verifyServiceToken(tokenString string) (bool, string, error) {
	// Add debug logging for k8s client config
	m.logger.Info("K8s client config",
		"host", m.k8sClient.RESTClient().Get().URL().Host,
		"scheme", m.k8sClient.RESTClient().Get().URL().Scheme)

	// Log the environment variables
	m.logger.Info("K8s environment",
		"KUBERNETES_SERVICE_HOST", os.Getenv("KUBERNETES_SERVICE_HOST"),
		"KUBERNETES_SERVICE_PORT", os.Getenv("KUBERNETES_SERVICE_PORT"))

	// Create TokenReview
	tokenReview := &authv1.TokenReview{
		Spec: authv1.TokenReviewSpec{
			Token:     tokenString,
			Audiences: []string{"https://kubernetes.default.svc.cluster.local"},
		},
	}

	m.logger.Infow("Token review request",
		"token_length", len(tokenString),
		"token_preview", tokenString[:10]+"..."+tokenString[len(tokenString)-10:],
		"audiences", tokenReview.Spec.Audiences)

	result, err := m.k8sClient.AuthenticationV1().TokenReviews().Create(context.Background(), tokenReview, metav1.CreateOptions{})
	if err != nil {
		m.logger.Errorw("Failed to review token",
			"error", err,
			"error_type", fmt.Sprintf("%T", err))
		return false, "", fmt.Errorf("token review failed: %v", err)
	}

	m.logger.Infow("Token review response",
		"authenticated", result.Status.Authenticated,
		"user", result.Status.User,
		"error", result.Status.Error)

	if !result.Status.Authenticated {
		m.logger.Errorw("Token not authenticated",
			"error", result.Status.Error,
			"user", result.Status.User)
		return false, "", nil
	}

	// Verify the service account name
	expectedServiceAccount := "recipe-agent-service"
	if !strings.HasPrefix(result.Status.User.Username, fmt.Sprintf("system:serviceaccount:default:%s", expectedServiceAccount)) {
		m.logger.Errorw("Invalid service account",
			"expected", expectedServiceAccount,
			"got", result.Status.User.Username)
		return false, "", nil
	}

	return true, result.Status.User.Username, nil
}
