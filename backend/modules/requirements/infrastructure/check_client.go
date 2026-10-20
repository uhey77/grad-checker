package infrastructure

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"grad-checker/backend/modules/requirements/application/ports"
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
func (c *PythonCheckClient) Call(ctx context.Context, call ports.CheckCall) (json.RawMessage, error) {
	data, err := c.client.Call(ctx, call)
	if err != nil {
		var failure *pythonbridge.BusinessError
		if errors.As(err, &failure) {
			return nil, &ports.EvaluationError{Code: failure.Code}
		}
		return nil, ports.ErrBackend
	}
	if call.Operation == "list" {
		if call.Page == nil || !validCheckList(data, *call.Page) {
			return nil, ports.ErrBackend
		}
		return data, nil
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
	if json.Unmarshal(data, &shape) != nil || len(shape.ID) != 36 || json.Unmarshal(shape.Input, &input) != nil || input.DataRevision == nil || input.Grades == nil || !validEvaluationResult(shape.Result, call.Operation == "get") {
		return nil, ports.ErrBackend
	}
	// 入力と結果は同じ成績版のスナップショットから作られている。
	if json.Unmarshal(shape.Result, &result) != nil || result.DataRevision != *input.DataRevision {
		return nil, ports.ErrBackend
	}
	if _, err := time.Parse(time.RFC3339Nano, shape.CreatedAt); err != nil {
		return nil, ports.ErrBackend
	}
	switch call.Operation {
	case "create":
		// 保存した履歴は要求した成績版で判定したものに限る。
		if call.Request == nil || *input.DataRevision != call.Request.ExpectedRevision {
			return nil, ports.ErrBackend
		}
	case "get":
		if shape.ID != call.CheckID {
			return nil, ports.ErrBackend
		}
	}
	return data, nil
}

// validCheckListは履歴一覧の要約と、要求した範囲・件数との対応を検証する。
func validCheckList(data json.RawMessage, page ports.CheckPage) bool {
	var shape struct {
		Checks *[]struct {
			ID           string `json:"id"`
			CreatedAt    string `json:"created_at"`
			DataRevision *int64 `json:"data_revision"`
			Result       string `json:"result"`
			Curriculum   *struct {
				ID       string `json:"id"`
				Name     string `json:"name"`
				Revision int64  `json:"revision"`
			} `json:"curriculum"`
			Total *creditTotal `json:"total"`
		} `json:"checks"`
		Limit      *int64 `json:"limit"`
		Offset     *int64 `json:"offset"`
		TotalCount *int64 `json:"total_count"`
	}
	if json.Unmarshal(data, &shape) != nil || shape.Checks == nil || shape.Limit == nil || shape.Offset == nil || shape.TotalCount == nil {
		return false
	}
	count := int64(len(*shape.Checks))
	if *shape.Limit != page.Limit || *shape.Offset != page.Offset || count > page.Limit || (count > 0 && page.Offset+count > *shape.TotalCount) || *shape.TotalCount < 0 {
		return false
	}
	for _, check := range *shape.Checks {
		if len(check.ID) != 36 || check.DataRevision == nil || *check.DataRevision < 0 || !judgment(check.Result) || check.Curriculum == nil || check.Curriculum.ID == "" || check.Curriculum.Name == "" || check.Curriculum.Revision < 1 || !check.Total.valid() {
			return false
		}
		if _, err := time.Parse(time.RFC3339Nano, check.CreatedAt); err != nil {
			return false
		}
	}
	return true
}
