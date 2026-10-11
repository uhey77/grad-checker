// Python内部サービスとのHTTP通信で、科目一覧の取得契約を実装する。
package infrastructure

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"net/url"
	"time"

	"grad-checker/backend/modules/subjects/application"
)

type PythonSubjectListClient struct {
	endpoint string
	client   *http.Client
}

func NewPythonSubjectListClient(origin string, timeout time.Duration) (*PythonSubjectListClient, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("python-urlにはパスを含まないhttp/httpsオリジンを指定してください。")
	}
	return &PythonSubjectListClient{
		endpoint: origin + "/internal/subject-list",
		client:   &http.Client{Timeout: timeout, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }},
	}, nil
}

func (c *PythonSubjectListClient) ListPrograms(ctx context.Context) (json.RawMessage, error) {
	return c.call(ctx, "list_programs", "")
}

func (c *PythonSubjectListClient) GetSubjectList(ctx context.Context, id string) (json.RawMessage, error) {
	return c.call(ctx, "get_subject_list", id)
}

func (c *PythonSubjectListClient) call(ctx context.Context, operation, id string) (json.RawMessage, error) {
	payload, err := json.Marshal(struct {
		Operation    string `json:"operation"`
		CurriculumID string `json:"curriculum_id,omitempty"`
	}{operation, id})
	if err != nil {
		return nil, err
	}
	r, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	r.Header.Set("Content-Type", "application/json")
	response, err := c.client.Do(r)
	if err != nil {
		var timeout net.Error
		if errors.Is(err, context.DeadlineExceeded) || (errors.As(err, &timeout) && timeout.Timeout()) {
			return nil, application.ErrTimeout
		}
		return nil, application.ErrUnavailable
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, application.ErrProtocol
	}
	var result struct {
		Data  json.RawMessage               `json:"data"`
		Error *application.SubjectListError `json:"error"`
	}
	decoder := json.NewDecoder(io.LimitReader(response.Body, 8<<20))
	if err := decoder.Decode(&result); err != nil {
		return nil, application.ErrProtocol
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return nil, application.ErrProtocol
	}
	if result.Error != nil {
		if len(result.Data) != 0 {
			return nil, application.ErrProtocol
		}
		return nil, result.Error
	}
	data := bytes.TrimSpace(result.Data)
	if len(data) == 0 || (operation == "list_programs" && data[0] != '[') || (operation == "get_subject_list" && data[0] != '{') {
		return nil, application.ErrProtocol
	}
	return data, nil
}
