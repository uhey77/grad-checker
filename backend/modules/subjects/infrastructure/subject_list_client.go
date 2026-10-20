// PythonサービスとのHTTP通信で、科目一覧の取得契約を実装する。
package infrastructure

import (
	"context"
	"encoding/json"
	"time"

	"grad-checker/backend/modules/shared/pythonbridge"
	"grad-checker/backend/modules/subjects/application/ports"
)

type PythonSubjectListClient struct {
	client *pythonbridge.Client
}

func NewPythonSubjectListClient(origin string, timeout time.Duration) (*PythonSubjectListClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/subject-list", timeout, 8<<20)
	if err != nil {
		return nil, err
	}
	return &PythonSubjectListClient{client}, nil
}

func (c *PythonSubjectListClient) ListPrograms(ctx context.Context) (json.RawMessage, error) {
	return c.call(ctx, "list_programs", "")
}

func (c *PythonSubjectListClient) GetSubjectList(ctx context.Context, id string) (json.RawMessage, error) {
	return c.call(ctx, "get_subject_list", id)
}

func (c *PythonSubjectListClient) call(ctx context.Context, operation, id string) (json.RawMessage, error) {
	data, err := c.client.Call(ctx, struct {
		Operation    string `json:"operation"`
		CurriculumID string `json:"curriculum_id,omitempty"`
	}{operation, id})
	if err != nil {
		return nil, subjectError(err, func(code string) error { return &ports.SubjectListError{Code: code} })
	}
	if (operation == "list_programs" && data[0] != '[') || (operation == "get_subject_list" && data[0] != '{') {
		return nil, ports.ErrProtocol
	}
	return data, nil
}
