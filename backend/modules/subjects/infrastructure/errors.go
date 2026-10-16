package infrastructure

import (
	"errors"

	"grad-checker/backend/modules/shared/internalhttp"
	"grad-checker/backend/modules/subjects/application"
)

// subjectErrorは内部通信の失敗を科目モジュールの取得契約のエラーへ変換する。
// 業務エラーコードは呼出し側の型へ詰め替える。
func subjectError(err error, business func(code string) error) error {
	var failure *internalhttp.BusinessError
	switch {
	case errors.As(err, &failure):
		return business(failure.Code)
	case errors.Is(err, internalhttp.ErrTimeout):
		return application.ErrTimeout
	case errors.Is(err, internalhttp.ErrUnavailable):
		return application.ErrUnavailable
	default:
		return application.ErrProtocol
	}
}
