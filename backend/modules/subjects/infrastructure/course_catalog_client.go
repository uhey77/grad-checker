package infrastructure

import (
	"context"
	"encoding/json"
	"time"

	"grad-checker/backend/modules/shared/internalhttp"
	"grad-checker/backend/modules/subjects/application"
)

// PythonCourseCatalogClientは学生向け科目一覧・分類の取得契約を内部HTTPで実装する。
type PythonCourseCatalogClient struct {
	client *internalhttp.Client
}

func NewPythonCourseCatalogClient(origin string, timeout time.Duration) (*PythonCourseCatalogClient, error) {
	client, err := internalhttp.New(origin, "/internal/courses", timeout, 8<<20)
	if err != nil {
		return nil, err
	}
	return &PythonCourseCatalogClient{client}, nil
}

func (c *PythonCourseCatalogClient) Call(ctx context.Context, call application.CourseCatalogCall) (json.RawMessage, error) {
	data, err := c.client.Call(ctx, call)
	if err != nil {
		return nil, subjectError(err, func(code string) error { return &application.CourseCatalogError{Code: code} })
	}
	// 課程情報と、操作に対応する配列だけを持つ応答を受け付ける。
	var shape struct {
		Curriculum *struct {
			CurriculumID string `json:"curriculum_id"`
		} `json:"curriculum"`
		Courses    *[]json.RawMessage `json:"courses"`
		Categories *[]json.RawMessage `json:"categories"`
	}
	if json.Unmarshal(data, &shape) != nil || shape.Curriculum == nil || shape.Curriculum.CurriculumID == "" {
		return nil, application.ErrProtocol
	}
	if (call.Operation == "courses" && (shape.Courses == nil || shape.Categories != nil)) || (call.Operation == "categories" && (shape.Categories == nil || shape.Courses != nil)) {
		return nil, application.ErrProtocol
	}
	return data, nil
}
