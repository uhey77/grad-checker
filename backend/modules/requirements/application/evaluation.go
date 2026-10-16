// Package applicationはPythonの判定ユースケースを呼び出す契約を定義する。
package application

import (
	"context"
	"encoding/json"
	"errors"
)

type EvaluationCall struct {
	Token string `json:"token"`
}

type EvaluationError struct{ Code string }

func (e *EvaluationError) Error() string { return e.Code }

var ErrBackend = errors.New("evaluation backend unavailable")

type EvaluationGateway interface {
	Call(context.Context, EvaluationCall) (json.RawMessage, error)
}
