package config

import (
	"github.com/karthik446/pantry_chef/api/internal/platform/env"
)

// HTTPConfig holds HTTP server configuration
type HTTPConfig struct {
	Port string `env:"HTTP_PORT" envDefault:"8000"`
}

// GRPCConfig holds gRPC server configuration
type GRPCConfig struct {
	Port string `env:"GRPC_PORT" envDefault:"9000"`
}

// DBConfig holds database configuration
type DBConfig struct {
	URL          string `env:"DB_URL,required"`
	MaxOpenConns int    `env:"DATABASE_MAX_OPEN_CONNS" envDefault:"25"`
}

// JWTConfig holds JWT configuration
type JWTConfig struct {
	Secret string `env:"JWT_SECRET,required"`
}

// Config holds all configuration for the application
type Config struct {
	HTTP    HTTPConfig
	GRPC    GRPCConfig
	DB      DBConfig
	JWT     JWTConfig
	Env     string
	Version string
}

func Load() (*Config, error) {
	cfg := Config{
		HTTP: HTTPConfig{
			Port: env.GetString("HTTP_PORT", "8000"),
		},
		GRPC: GRPCConfig{
			Port: env.GetString("GRPC_PORT", "9000"),
		},
		DB: DBConfig{
			URL:          env.GetString("DB_URL", ""),
			MaxOpenConns: env.GetInt("DB_MAX_OPEN_CONNS", 25),
		},
		JWT: JWTConfig{
			Secret: env.GetString("JWT_SECRET", "your-secret-key"),
		},
		Env:     env.GetString("NODE_ENV", "development"),
		Version: env.GetString("VERSION", "1.0.0"),
	}

	return &cfg, nil
}
