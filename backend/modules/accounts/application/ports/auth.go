package ports

import (
	"context"
	"errors"
)

type AuthCall struct {
	Operation    string `json:"operation"`
	LoginName    string `json:"login_name,omitempty"`
	RecoveryCode string `json:"recovery_code,omitempty"`
	Password     string `json:"password,omitempty"`
	Token        string `json:"token,omitempty"`
	CSRF         string `json:"csrf,omitempty"`
	ClientKey    string `json:"client_key,omitempty"`
}

type Student struct {
	ID        string `json:"id"`
	LoginName string `json:"login_name"`
}

type AuthPolicy struct {
	PasswordMinLength int `json:"password_min_length"`
	PasswordMaxLength int `json:"password_max_length"`
}

type AuthResult struct {
	Policy        *AuthPolicy `json:"policy,omitempty"`
	Registered    bool        `json:"registered,omitempty"`
	Recovered     bool        `json:"recovered,omitempty"`
	RecoveryCode  string      `json:"recovery_code,omitempty"`
	Authenticated bool        `json:"authenticated"`
	Student       *Student    `json:"student,omitempty"`
	CSRFToken     string      `json:"csrf_token,omitempty"`
	ExpiresAt     string      `json:"expires_at,omitempty"`
	SessionToken  string      `json:"session_token,omitempty"`
}

type AuthError struct {
	Code string `json:"code"`
}

func (e *AuthError) Error() string { return e.Code }

var ErrBackend = errors.New("authentication backend unavailable")

type AuthGateway interface {
	Call(context.Context, AuthCall) (AuthResult, error)
}
