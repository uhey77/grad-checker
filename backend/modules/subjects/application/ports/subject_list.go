// 科目一覧のユースケースを言語間で呼び出す契約を定義する。
package ports

import (
	"context"
	"encoding/json"
	"errors"
)

// SubjectListReaderはPythonの科目一覧ユースケースを呼ぶ取得先の契約。
// 結果は既存の科目モデルに従うJSONとし、DBモデルやブリッジ通信の包絡形式は渡さない。
type SubjectListReader interface {
	ListPrograms(context.Context) (json.RawMessage, error)
	GetSubjectList(context.Context, string) (json.RawMessage, error)
}

type SubjectListError struct {
	Code string `json:"code"`
}

func (e *SubjectListError) Error() string { return e.Code }

var (
	ErrUnavailable = errors.New("python service unavailable")
	ErrTimeout     = errors.New("python service timeout")
	ErrProtocol    = errors.New("invalid bridge response")
)
