// PythonサービスとのHTTP通信で、本人成績の取得契約を実装する。
package infrastructure

import (
	"context"
	"errors"
	"time"

	"grad-checker/backend/modules/grades/application/ports"
	"grad-checker/backend/shared/pythonbridge"
)

type PythonGradeClient struct {
	client *pythonbridge.Client
}

func NewPythonGradeClient(origin string) (*PythonGradeClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/grades", 10*time.Second, 1024*1024)
	if err != nil {
		return nil, err
	}
	return &PythonGradeClient{client}, nil
}

func (c *PythonGradeClient) Call(ctx context.Context, call ports.GradeCall) (ports.StudentGrades, error) {
	var empty ports.StudentGrades
	raw, err := c.client.Call(ctx, call)
	if err != nil {
		var failure *pythonbridge.BusinessError
		if errors.As(err, &failure) {
			return empty, &ports.GradeError{Code: failure.Code}
		}
		return empty, ports.ErrBackend
	}
	var data ports.StudentGrades
	if pythonbridge.DecodeData(raw, &data) != nil {
		return empty, ports.ErrBackend
	}
	if data.Grades == nil || data.DataRevision < 0 {
		return empty, ports.ErrBackend
	}
	for _, g := range data.Grades {
		if g.CourseID == "" || g.AttemptNo < 1 || (g.ResultStatus == "finalized") != (g.GradeCode != nil) || (g.ResultStatus != "finalized" && g.ResultStatus != "pending") {
			return empty, ports.ErrBackend
		}
	}
	if call.Operation == "save" && (call.GradeSet == nil || data.DataRevision != call.GradeSet.ExpectedRevision+1 || len(data.Grades) != len(call.GradeSet.Grades)) {
		return empty, ports.ErrBackend
	}
	return data, nil
}
