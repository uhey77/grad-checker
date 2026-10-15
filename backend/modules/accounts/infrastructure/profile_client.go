package infrastructure

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"grad-checker/backend/modules/accounts/application"
)

type PythonProfileClient struct{ auth *PythonAuthClient }

func NewPythonProfileClient(origin string) (*PythonProfileClient, error) {
	auth, err := NewPythonAuthClient(origin)
	if err != nil {
		return nil, err
	}
	return &PythonProfileClient{auth}, nil
}

func (c *PythonProfileClient) Call(ctx context.Context, call application.ProfileCall) (application.ProfileResult, error) {
	var empty application.ProfileResult
	body, err := json.Marshal(call)
	if err != nil {
		return empty, application.ErrBackend
	}
	endpoint := strings.TrimSuffix(c.auth.endpoint, "/auth") + "/profile"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return empty, application.ErrBackend
	}
	req.Header.Set("Content-Type", "application/json")
	response, err := c.auth.client.Do(req)
	if err != nil {
		return empty, application.ErrBackend
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return empty, application.ErrBackend
	}
	var result struct {
		Data  *application.ProfileResult `json:"data"`
		Error *application.AuthError     `json:"error"`
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
		return empty, result.Error
	}
	data := *result.Data
	if call.Operation == "programs" {
		if data.Programs == nil || data.Profile != nil {
			return empty, application.ErrBackend
		}
		for _, p := range *data.Programs {
			if p.ProgramID == "" || p.CurriculumID == "" || p.FacultyName == "" || p.CurriculumName == "" || p.Revision < 1 || (p.VerificationStatus != "verified" && p.VerificationStatus != "unverified") || p.SourceDocument == "" || p.SourcePages == "" {
				return empty, application.ErrBackend
			}
		}
	} else {
		p := data.Profile
		if p == nil || data.Programs != nil || p.StudentID == "" || p.LoginName == "" || p.DataRevision < 0 || (p.ProgramID == nil) != (p.CurriculumID == nil) {
			return empty, application.ErrBackend
		}
		if call.Operation == "save_program" && (call.Selection == nil || p.ProgramID == nil || *p.ProgramID != call.Selection.ProgramID || *p.CurriculumID != call.Selection.CurriculumID || p.DataRevision != call.Selection.ExpectedRevision+1) {
			return empty, application.ErrBackend
		}
	}
	return data, nil
}
