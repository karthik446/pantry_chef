package config

import (
	"github.com/karthik446/pantry_chef/api/internal/platform/env"
)

type Config struct {
	Addr    string
	DB      DBConfig
	Env     string
	Version string
}

type DBConfig struct {
	Addr         string
	MaxOpenConns int
	MaxIdleConns int
	MaxIdleTime  string
}

func Load() (*Config, error) {
	cfg := Config{
		Addr: env.GetString("PORT", "8000"),
		DB: DBConfig{
			Addr:         env.GetString("SUPABASE_DB_URL", ""),
			MaxOpenConns: env.GetInt("DB_MAX_OPEN_CONNS", 25),
			MaxIdleConns: env.GetInt("DB_MAX_IDLE_CONNS", 20),
			MaxIdleTime:  env.GetString("DB_MAX_IDLE_TIME", "15m"),
		},
		Env:     env.GetString("NODE_ENV", "development"),
		Version: env.GetString("VERSION", "1.0.0"),
	}

	return &cfg, nil
}
