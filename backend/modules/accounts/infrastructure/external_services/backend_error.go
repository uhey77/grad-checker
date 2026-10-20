package infrastructure

import (
	"errors"

	"grad-checker/backend/modules/accounts/application/ports"
	"grad-checker/backend/shared/pythonbridge"
)

// accountErrorはブリッジ通信の失敗をアカウントモジュールの取得契約のエラーへ変換する。
// 業務エラーはコードを保ち、通信失敗・包絡形式の違反はErrBackendにまとめる。
func accountError(err error) error {
	var failure *pythonbridge.BusinessError
	if errors.As(err, &failure) {
		return &ports.AuthError{Code: failure.Code}
	}
	return ports.ErrBackend
}
