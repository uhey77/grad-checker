// Python内部サービスとのHTTP通信で、本人成績の取得契約を実装する。
package infrastructure

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"time"

	"grad-checker/backend/modules/grades/application"
)

type PythonGradeClient struct {
	endpoint string
	client   *http.Client
}

func NewPythonGradeClient(origin string) (*PythonGradeClient, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("python-urlにはhttp/httpsオリジンを指定してください。")
	}
	return &PythonGradeClient{origin + "/internal/grades", &http.Client{Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}, nil
}

func (c *PythonGradeClient) Call(ctx context.Context, call application.GradeCall) (application.StudentGrades, error) {
	var empty application.StudentGrades
	body, err := json.Marshal(call)
	if err != nil {
		return empty, application.ErrBackend
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(body))
	if err != nil {
		return empty, application.ErrBackend
	}
	req.Header.Set("Content-Type", "application/json")
	response, err := c.client.Do(req)
	if err != nil {
		return empty, application.ErrBackend
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return empty, application.ErrBackend
	}
	var result struct {
		Data  *application.StudentGrades `json:"data"`
		Error *application.GradeError    `json:"error"`
	}
	decoder := json.NewDecoder(io.LimitReader(response.Body, 1024*1024))
	decoder.DisallowUnknownFields()
	if decoder.Decode(&result) != nil {
		return empty, application.ErrBackend
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF || (result.Data == nil) == (result.Error == nil) {
		return empty, application.ErrBackend
	}
	if result.Error != nil {
		if result.Error.Code == "" {
			return empty, application.ErrBackend
		}
		return empty, result.Error
	}
	data := *result.Data
	if data.Grades == nil || data.DataRevision < 0 {
		return empty, application.ErrBackend
	}
	for _, g := range data.Grades {
		if g.CourseID == "" || g.AttemptNo < 1 || (g.ResultStatus == "finalized") != (g.GradeCode != nil) || (g.ResultStatus != "finalized" && g.ResultStatus != "pending") {
			return empty, application.ErrBackend
		}
	}
	if call.Operation == "save" && (call.GradeSet == nil || data.DataRevision != call.GradeSet.ExpectedRevision+1 || len(data.Grades) != len(call.GradeSet.Grades)) {
		return empty, application.ErrBackend
	}
	return data, nil
}
