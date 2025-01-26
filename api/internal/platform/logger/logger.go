package logger

import (
	"os"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Currently not used
var log *zap.Logger

func init() {
	// Configure file rotation
	logWriter := &lumberjack.Logger{
		Filename:   "logs/api.log",
		MaxSize:    10, // MB
		MaxBackups: 5,
		MaxAge:     30,   // days
		Compress:   true, // compress rotated files
	}

	// Configure JSON encoder for file output
	jsonConfig := zap.NewProductionEncoderConfig()
	jsonConfig.TimeKey = "timestamp"
	jsonConfig.EncodeTime = zapcore.TimeEncoderOfLayout(time.RFC3339)
	jsonConfig.EncodeLevel = zapcore.CapitalLevelEncoder
	jsonConfig.EncodeDuration = zapcore.StringDurationEncoder
	jsonConfig.StacktraceKey = ""

	// Configure console encoder with colors
	consoleConfig := zap.NewDevelopmentEncoderConfig()
	consoleConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	consoleConfig.EncodeTime = zapcore.TimeEncoderOfLayout("2006-01-02 15:04:05")
	consoleConfig.EncodeDuration = zapcore.StringDurationEncoder
	consoleConfig.EncodeCaller = zapcore.ShortCallerEncoder

	// Create core with both JSON file output and colored console output
	core := zapcore.NewTee(
		zapcore.NewCore(
			zapcore.NewJSONEncoder(jsonConfig),
			zapcore.AddSync(logWriter),
			zapcore.InfoLevel,
		),
		zapcore.NewCore(
			zapcore.NewConsoleEncoder(consoleConfig),
			zapcore.AddSync(os.Stdout),
			zapcore.DebugLevel,
		),
	)

	// Create logger
	log = zap.New(core)
}

// GetLogger returns the configured logger
func GetLogger() *zap.Logger {
	return log
}

// Info logs info level message
func Info(msg string, fields ...zapcore.Field) {
	log.Info(msg, fields...)
}

// Error logs error level message
func Error(msg string, fields ...zapcore.Field) {
	log.Error(msg, fields...)
}

// Debug logs debug level message
func Debug(msg string, fields ...zapcore.Field) {
	log.Debug(msg, fields...)
}

// Fatal logs fatal level message and exits
func Fatal(msg string, fields ...zapcore.Field) {
	log.Fatal(msg, fields...)
}

// WithRequestID adds request ID to logger context
func WithRequestID(requestID string) *zap.Logger {
	return log.With(zap.String("request_id", requestID))
}
