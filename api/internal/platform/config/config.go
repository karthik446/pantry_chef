package config

import (
	"fmt"

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
	Host         string `env:"DB_HOST" envDefault:"postgres-postgresql.infrastructure.svc.cluster.local"`
	Port         string `env:"DB_PORT" envDefault:"5432"`
	User         string `env:"DB_USER" envDefault:"postgres"`
	Password     string `env:"DB_PASSWORD,required"`
	DBName       string `env:"DB_NAME" envDefault:"pantry_chef"`
	MaxOpenConns int    `env:"DATABASE_MAX_OPEN_CONNS" envDefault:"25"`
}

// JWTConfig holds JWT configuration
type JWTConfig struct {
	Secret string `env:"JWT_SECRET,required"`
}

type RabbitMQConfig struct {
	URL string `env:"RABBITMQ_URL,required"`
}

// Config holds all configuration for the application
type Config struct {
	HTTP     HTTPConfig
	GRPC     GRPCConfig
	DB       DBConfig
	JWT      JWTConfig
	RabbitMQ RabbitMQConfig
	Env      string
	Version  string
}

func (c *DBConfig) GetURL() string {
	return fmt.Sprintf("postgresql://%s:%s@%s:%s/%s?sslmode=disable",
		c.User, c.Password, c.Host, c.Port, c.DBName)
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
			Host:         env.GetString("DB_HOST", "postgres-postgresql.infrastructure.svc.cluster.local"),
			Port:         env.GetString("DB_PORT", "5432"),
			User:         env.GetString("DB_USER", "postgres"),
			Password:     env.GetString("DB_PASSWORD", ""),
			DBName:       env.GetString("DB_NAME", "pantry_chef"),
			MaxOpenConns: env.GetInt("DATABASE_MAX_OPEN_CONNS", 25),
		},
		JWT: JWTConfig{
			Secret: env.GetString("JWT_SECRET", "your-secret-key"),
		},
		Env:     env.GetString("NODE_ENV", "development"),
		Version: env.GetString("VERSION", "1.0.0"),
		RabbitMQ: RabbitMQConfig{
			URL: env.GetString("RABBITMQ_URL", "amqp://user:rabbitmq@rabbitmq.infrastructure.svc.cluster.local:5672/"),
		},
	}

	return &cfg, nil
}
