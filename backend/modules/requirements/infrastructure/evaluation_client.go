package infrastructure

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"grad-checker/backend/modules/requirements/application"
	"grad-checker/backend/modules/shared/pythonbridge"
)

type PythonEvaluationClient struct{ client *pythonbridge.Client }

func NewPythonEvaluationClient(origin string) (*PythonEvaluationClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/graduation-requirements", 10*time.Second, 8<<20)
	if err != nil {
		return nil, err
	}
	return &PythonEvaluationClient{client}, nil
}

// 単位計算はPythonに限定し、Goは応答契約の形だけを検証する。
func (c *PythonEvaluationClient) Call(ctx context.Context, call application.EvaluationCall) (json.RawMessage, error) {
	data, err := c.client.Call(ctx, call)
	if err != nil {
		var failure *pythonbridge.BusinessError
		if errors.As(err, &failure) {
			return nil, &application.EvaluationError{Code: failure.Code}
		}
		return nil, application.ErrBackend
	}
	var shape struct {
		Result       string `json:"result"`
		DataRevision *int64 `json:"data_revision"`
		EvaluatedAt  string `json:"evaluated_at"`
		Curriculum   *struct {
			ID       string `json:"id"`
			Revision *int64 `json:"revision"`
		} `json:"curriculum"`
		Total *struct {
			Required *int64 `json:"required_credits"`
			Earned   *int64 `json:"earned_credits"`
			Credited *int64 `json:"credited_credits"`
			Shortage *int64 `json:"shortage"`
			Result   string `json:"result"`
		} `json:"total"`
		Requirements        *[]json.RawMessage `json:"requirements"`
		Categories          *[]json.RawMessage `json:"categories"`
		Missing             *[]json.RawMessage `json:"missing_required_courses"`
		Courses             *[]json.RawMessage `json:"courses"`
		Allocations         *[]json.RawMessage `json:"allocations"`
		ExternalAllocations *[]json.RawMessage `json:"external_allocations"`
		Warnings            *[]string          `json:"warnings"`
		RuleRevisions       map[string]int64   `json:"rule_revisions"`
	}
	if json.Unmarshal(data, &shape) != nil || !judgment(shape.Result) || shape.DataRevision == nil || *shape.DataRevision < 0 || shape.Curriculum == nil || shape.Curriculum.ID == "" || shape.Curriculum.Revision == nil || *shape.Curriculum.Revision < 1 || shape.Total == nil || shape.Requirements == nil || len(*shape.Requirements) == 0 || shape.Categories == nil || shape.Missing == nil || shape.Courses == nil || shape.Allocations == nil || shape.ExternalAllocations == nil || shape.Warnings == nil || shape.RuleRevisions == nil {
		return nil, application.ErrBackend
	}
	if _, err := time.Parse(time.RFC3339Nano, shape.EvaluatedAt); err != nil {
		return nil, application.ErrBackend
	}
	for _, value := range []*int64{shape.Total.Required, shape.Total.Earned, shape.Total.Credited, shape.Total.Shortage} {
		if value == nil || *value < 0 {
			return nil, application.ErrBackend
		}
	}
	if !judgment(shape.Total.Result) {
		return nil, application.ErrBackend
	}
	return data, nil
}

func judgment(value string) bool { return value == "pass" || value == "fail" }
