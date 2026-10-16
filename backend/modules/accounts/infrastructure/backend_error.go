package infrastructure

import (
	"errors"

	"grad-checker/backend/modules/accounts/application"
	"grad-checker/backend/modules/shared/internalhttp"
)

// accountErrorは内部通信の失敗をアカウントモジュールの取得契約のエラーへ変換する。
// 業務エラーはコードを保ち、通信失敗・包絡形式の違反はErrBackendにまとめる。
func accountError(err error) error {
	var failure *internalhttp.BusinessError
	if errors.As(err, &failure) {
		return &application.AuthError{Code: failure.Code}
	}
	return application.ErrBackend
}
