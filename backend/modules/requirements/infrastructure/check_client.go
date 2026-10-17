package infrastructure

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"grad-checker/backend/modules/requirements/application"
	"grad-checker/backend/modules/shared/pythonbridge"
)

type PythonCheckClient struct{ client *pythonbridge.Client }

func NewPythonCheckClient(origin string) (*PythonCheckClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/checks", 10*time.Second, 16<<20)
	if err != nil {
		return nil, err
	}
	return &PythonCheckClient{client}, nil
}

// 判定と保存はPythonに限定し、Goは保存済み履歴の形と要求との対応だけを検証する。
func (c *PythonCheckClient) Call(ctx context.Context, call application.CheckCall) (json.RawMessage, error) {
	data, err := c.client.Call(ctx, call)
	if err != nil {
		var failure *pythonbridge.BusinessError
		if errors.As(err, &failure) {
			return nil, &application.EvaluationError{Code: failure.Code}
		}
		return nil, application.ErrBackend
	}
	var shape struct {
		ID        string          `json:"id"`
		CreatedAt string          `json:"created_at"`
		Input     json.RawMessage `json:"input"`
		Result    json.RawMessage `json:"result"`
	}
	var input struct {
		DataRevision *int64             `json:"data_revision"`
		Grades       *[]json.RawMessage `json:"grades"`
	}
	var result struct {
		DataRevision int64 `json:"data_revision"`
	}
	if json.Unmarshal(data, &shape) != nil || len(shape.ID) != 36 || json.Unmarshal(shape.Input, &input) != nil || input.DataRevision == nil || input.Grades == nil || !validEvaluation(shape.Result) {
		return nil, application.ErrBackend
	}
	// 入力と結果は同じ成績版のスナップショットから作られている。
	if json.Unmarshal(shape.Result, &result) != nil || result.DataRevision != *input.DataRevision {
		return nil, application.ErrBackend
	}
	if _, err := time.Parse(time.RFC3339Nano, shape.CreatedAt); err != nil {
		return nil, application.ErrBackend
	}
	switch call.Operation {
	case "create":
		// 保存した履歴は要求した成績版で判定したものに限る。
		if call.Request == nil || *input.DataRevision != call.Request.ExpectedRevision {
			return nil, application.ErrBackend
		}
	case "get":
		if shape.ID != call.CheckID {
			return nil, application.ErrBackend
		}
	}
	return data, nil
}
