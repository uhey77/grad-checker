package infrastructure

import (
	"context"
	"time"

	"grad-checker/backend/modules/accounts/application"
	"grad-checker/backend/modules/shared/pythonbridge"
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

func (c *PythonProfileClient) Call(ctx context.Context, call application.ProfileCall) (application.ProfileResult, error) {
	var empty application.ProfileResult
	raw, err := c.client.Call(ctx, call)
	if err != nil {
		return empty, accountError(err)
	}
	var data application.ProfileResult
	if pythonbridge.DecodeData(raw, &data) != nil {
		return empty, application.ErrBackend
	}
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
