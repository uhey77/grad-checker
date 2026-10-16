package application

import (
	"context"
	"encoding/json"
)

// CourseFiltersは学生向け科目一覧の絞り込み。複数指定はANDで、空文字は未指定。
type CourseFilters struct {
	CategoryID string `json:"category_id,omitempty"`
	Faculty    string `json:"faculty,omitempty"`
	Department string `json:"department,omitempty"`
	Semester   string `json:"semester,omitempty"`
	Q          string `json:"q,omitempty"`
}

type CourseCatalogCall struct {
	Operation string         `json:"operation"`
	Token     string         `json:"token"`
	Filters   *CourseFilters `json:"filters,omitempty"`
}

type CourseCatalogError struct {
	Code string `json:"code"`
}

func (e *CourseCatalogError) Error() string { return e.Code }

// CourseCatalogReaderは本人課程から見た科目・分類を取得する契約。
// 結果は既存の科目モデルに従うJSONとし、ブリッジ通信の包絡形式は渡さない。
type CourseCatalogReader interface {
	Call(context.Context, CourseCatalogCall) (json.RawMessage, error)
}
