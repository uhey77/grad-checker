package application

import (
	"context"
	"encoding/json"
)

// CheckRequestは判定対象とする本人の成績版。
type CheckRequest struct {
	ExpectedRevision int64 `json:"expected_revision"`
}

// CheckPageは本人の履歴一覧の取得範囲。作成日時の降順・同時刻はID順に数える。
type CheckPage struct {
	Limit  int64 `json:"limit"`
	Offset int64 `json:"offset"`
}

// CheckCallは判定履歴の保存（create）、本人の一覧（list）と本人限定の取得（get）を表す。
type CheckCall struct {
	Operation string        `json:"operation"`
	Token     string        `json:"token"`
	CSRF      string        `json:"csrf,omitempty"`
	Request   *CheckRequest `json:"request,omitempty"`
	Page      *CheckPage    `json:"page,omitempty"`
	CheckID   string        `json:"check_id,omitempty"`
}

type CheckGateway interface {
	Call(context.Context, CheckCall) (json.RawMessage, error)
}
