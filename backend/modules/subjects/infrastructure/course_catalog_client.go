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

// PythonCourseCatalogClientは学生向け科目一覧・分類の取得契約を内部HTTPで実装する。
type PythonCourseCatalogClient struct {
	endpoint string
	client   *http.Client
}

func NewPythonCourseCatalogClient(origin string, timeout time.Duration) (*PythonCourseCatalogClient, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("python-urlにはパスを含まないhttp/httpsオリジンを指定してください。")
	}
	return &PythonCourseCatalogClient{
		endpoint: origin + "/internal/courses",
		client:   &http.Client{Timeout: timeout, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }},
	}, nil
}

func (c *PythonCourseCatalogClient) Call(ctx context.Context, call application.CourseCatalogCall) (json.RawMessage, error) {
	payload, err := json.Marshal(call)
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
		Data  json.RawMessage                 `json:"data"`
		Error *application.CourseCatalogError `json:"error"`
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
		if len(result.Data) != 0 || result.Error.Code == "" {
			return nil, application.ErrProtocol
		}
		return nil, result.Error
	}
	// 課程情報と、操作に対応する配列だけを持つ応答を受け付ける。
	var shape struct {
		Curriculum *struct {
			CurriculumID string `json:"curriculum_id"`
		} `json:"curriculum"`
		Courses    *[]json.RawMessage `json:"courses"`
		Categories *[]json.RawMessage `json:"categories"`
	}
	if json.Unmarshal(result.Data, &shape) != nil || shape.Curriculum == nil || shape.Curriculum.CurriculumID == "" {
		return nil, application.ErrProtocol
	}
	if (call.Operation == "courses" && (shape.Courses == nil || shape.Categories != nil)) || (call.Operation == "categories" && (shape.Categories == nil || shape.Courses != nil)) {
		return nil, application.ErrProtocol
	}
	return bytes.TrimSpace(result.Data), nil
}
