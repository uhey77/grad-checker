package infrastructure

import (
	"context"
	"encoding/json"
	"time"

	"grad-checker/backend/modules/accounts/application/ports"
	"grad-checker/backend/shared/pythonbridge"
)

type PythonProfileClient struct {
	client *pythonbridge.Client
}

func NewPythonProfileClient(origin string) (*PythonProfileClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/profile", 10*time.Second, 1024*1024)
	if err != nil {
		return nil, err
	}
	return &PythonProfileClient{client}, nil
}

func (c *PythonProfileClient) Call(ctx context.Context, call ports.ProfileCall) (ports.ProfileResult, error) {
	var empty ports.ProfileResult
	raw, err := c.client.Call(ctx, call)
	if err != nil {
		return empty, accountError(err)
	}
	var data ports.ProfileResult
	if pythonbridge.DecodeData(raw, &data) != nil {
		return empty, ports.ErrBackend
	}
	if call.Operation == "programs" {
		if data.Programs == nil || data.Profile != nil {
			return empty, ports.ErrBackend
		}
		for _, p := range *data.Programs {
			if p.ProgramID == "" || p.CurriculumID == "" || p.FacultyName == "" || p.CurriculumName == "" || p.Revision < 1 || (p.VerificationStatus != "verified" && p.VerificationStatus != "unverified") || p.SourceDocument == "" || p.SourcePages == "" || !validCompletionPolicy(p.CompletionPolicy) {
				return empty, ports.ErrBackend
			}
		}
	} else {
		p := data.Profile
		if p == nil || data.Programs != nil || p.StudentID == "" || p.LoginName == "" || p.DataRevision < 0 || (p.ProgramID == nil) != (p.CurriculumID == nil) {
			return empty, ports.ErrBackend
		}
		if call.Operation == "save_program" && (call.Selection == nil || p.ProgramID == nil || *p.ProgramID != call.Selection.ProgramID || *p.CurriculumID != call.Selection.CurriculumID || p.DataRevision != call.Selection.ExpectedRevision+1) {
			return empty, ports.ErrBackend
		}
	}
	return data, nil
}

func validCompletionPolicy(raw json.RawMessage) bool {
	if len(raw) == 0 || string(raw) == "null" {
		return true
	}
	var value struct {
		Degree       string    `json:"degree_level"`
		Campus       string    `json:"campus"`
		Catalog      string    `json:"catalog_status"`
		Requirements string    `json:"requirements_status"`
		Rules        string    `json:"rules_status"`
		Reasons      *[]string `json:"unresolved_reasons"`
		Source       string    `json:"source_document"`
		Pages        string    `json:"source_pages"`
		Conditions   *[]struct {
			Code   string `json:"code"`
			Name   string `json:"name"`
			Source string `json:"source_document"`
			Pages  string `json:"source_pages"`
		} `json:"non_credit_conditions"`
	}
	if json.Unmarshal(raw, &value) != nil || (value.Degree != "bachelor" && value.Degree != "master" && value.Degree != "doctoral") || (value.Campus != "hachioji" && value.Campus != "kamata") || value.Reasons == nil || value.Conditions == nil || value.Source == "" || value.Pages == "" {
		return false
	}
	for _, status := range []string{value.Catalog, value.Requirements, value.Rules} {
		if status != "verified" && status != "unverified" {
			return false
		}
	}
	seen := map[string]bool{}
	for _, condition := range *value.Conditions {
		if condition.Code == "" || seen[condition.Code] || condition.Name == "" || condition.Source == "" || condition.Pages == "" {
			return false
		}
		seen[condition.Code] = true
	}
	return true
}
