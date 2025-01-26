package config

import (
	"github.com/karthik446/pantry_chef/api/internal/platform/env"
)

type Config struct {
	Addr string
	DB   struct {
		URL          string
		MaxOpenConns int
	}
	JWT struct {
		Secret string
	}
	Env     string
	Version string
}

func Load() (*Config, error) {
	cfg := Config{
		Addr: env.GetString("PORT", "8000"),
		DB: struct {
			URL          string
			MaxOpenConns int
		}{
			URL:          env.GetString("DB_URL", ""),
			MaxOpenConns: env.GetInt("DB_MAX_OPEN_CONNS", 25),
		},
		JWT: struct {
			Secret string
		}{
			Secret: env.GetString("JWT_SECRET", "your-secret-key"),
		},
		Env:     env.GetString("NODE_ENV", "development"),
		Version: env.GetString("VERSION", "1.0.0"),
	}

	return &cfg, nil
}
