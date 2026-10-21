package infrastructure

import (
	"errors"

	"grad-checker/backend/modules/subjects/application/ports"
	"grad-checker/backend/shared/pythonbridge"
)

// subjectErrorはブリッジ通信の失敗を科目モジュールの取得契約のエラーへ変換する。
// 業務エラーコードは呼出し側の型へ詰め替える。
func subjectError(err error, business func(code string) error) error {
	var failure *pythonbridge.BusinessError
	switch {
	case errors.As(err, &failure):
		return business(failure.Code)
	case errors.Is(err, pythonbridge.ErrTimeout):
		return ports.ErrTimeout
	case errors.Is(err, pythonbridge.ErrUnavailable):
		return ports.ErrUnavailable
	default:
		return ports.ErrProtocol
	}
}
