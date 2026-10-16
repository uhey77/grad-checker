package presentation

import (
	"encoding/json"
	"errors"
	"io"
	"mime"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"grad-checker/backend/modules/accounts/application"
)

const sessionCookie = "grad_checker_session"

type AuthHandler struct {
	gateway application.AuthGateway
	origin  string
	secure  bool
}

func NewAuthHandler(gateway application.AuthGateway, origin string, fallback http.Handler) (http.Handler, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" || (u.Scheme != "https" && u.Scheme != "http") {
		return nil, errors.New("public-originにはhttp/httpsオリジンを指定してください。")
	}
	if u.Scheme == "http" && u.Hostname() != "127.0.0.1" && u.Hostname() != "localhost" && u.Hostname() != "::1" {
		return nil, errors.New("公開環境の認証にはHTTPSが必要です。")
	}
	handler := &AuthHandler{gateway, origin, u.Scheme == "https"}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.URL.Path, "/api/auth/") {
			fallback.ServeHTTP(w, r)
			return
		}
		handler.ServeHTTP(w, r)
	}), nil
}
func (h *AuthHandler) cookie(w http.ResponseWriter, token string, expires time.Time, age int) {
	http.SetCookie(w, &http.Cookie{Name: sessionCookie, Value: token, Path: "/", HttpOnly: true, Secure: h.secure, SameSite: http.SameSiteLaxMode, Expires: expires, MaxAge: age})
}
func (h *AuthHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Referrer-Policy", "no-referrer")
	operation := strings.TrimPrefix(r.URL.Path, "/api/auth/")
	method := http.MethodPost
	if operation == "session" || operation == "config" {
		method = http.MethodGet
	}
	allowed := map[string]bool{"config": true, "register": true, "recover": true, "login": true, "session": true, "logout": true}
	if !allowed[operation] {
		writeError(w, 404, "APIが見つかりません。")
		return
	}
	if !allowMethod(w, r, method) || rejectQuery(w, r) {
		return
	}
	if method == http.MethodPost && r.Header.Get("Origin") != h.origin {
		writeError(w, 403, "アクセス元を確認できません。画面を再読み込みしてください。")
		return
	}
	call := application.AuthCall{Operation: operation}
	if operation == "register" || operation == "recover" || operation == "login" {
		media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if err != nil || media != "application/json" {
			writeError(w, 422, "JSON形式で入力してください。")
			return
		}
		decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192))
		token, err := decoder.Token()
		if err != nil || token != json.Delim('{') {
			writeError(w, 422, "入力形式が不正です。")
			return
		}
		fields := map[string]string{}
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				writeError(w, 422, "入力形式が不正です。")
				return
			}
			key, ok := keyToken.(string)
			if !ok {
				writeError(w, 422, "入力形式が不正です。")
				return
			}
			if _, duplicate := fields[key]; duplicate {
				writeError(w, 422, "入力項目が重複しています。")
				return
			}
			var value string
			if decoder.Decode(&value) != nil {
				writeError(w, 422, "入力項目は文字列で指定してください。")
				return
			}
			fields[key] = value
		}
		if token, err = decoder.Token(); err != nil || token != json.Delim('}') {
			writeError(w, 422, "入力形式が不正です。")
			return
		}
		var trailing any
		if decoder.Decode(&trailing) != io.EOF {
			writeError(w, 422, "入力形式が不正です。")
			return
		}
		expected := map[string]bool{"login_name": true, "password": true}
		if operation == "recover" {
			expected["recovery_code"] = true
		}
		if len(fields) != len(expected) {
			writeError(w, 422, "必要な入力項目を指定してください。")
			return
		}
		for key, value := range fields {
			if !expected[key] || value == "" {
				writeError(w, 422, "入力項目が不正です。")
				return
			}
		}
		call.LoginName, call.Password, call.RecoveryCode = fields["login_name"], fields["password"], fields["recovery_code"]
		if len(call.LoginName) > 32 || len([]rune(call.Password)) > 1024 || len(call.RecoveryCode) > 128 {
			writeError(w, 422, "入力が長すぎます。")
			return
		}
		host, _, err := net.SplitHostPort(r.RemoteAddr)
		if err != nil || net.ParseIP(host) == nil {
			writeError(w, 400, "接続元を確認できません。")
			return
		}
		call.ClientKey = host // Forwardedヘッダーは信頼しない。
	} else if operation != "config" {
		cookie, err := r.Cookie(sessionCookie)
		if err != nil || len(cookie.Value) != 43 {
			h.cookie(w, "", time.Time{}, -1)
			writeError(w, 401, "ログインしてください。")
			return
		}
		call.Token = cookie.Value
		if operation == "logout" {
			call.CSRF = r.Header.Get("X-CSRF-Token")
			if len(call.CSRF) != 64 {
				writeError(w, 403, "操作を確認できません。画面を再読み込みしてください。")
				return
			}
		}
	}
	result, err := h.gateway.Call(r.Context(), call)
	if err != nil {
		var business *application.AuthError
		if errors.As(err, &business) {
			if business.Code == "invalid_credentials" && (operation == "session" || operation == "config") {
				h.cookie(w, "", time.Time{}, -1)
			}
			writeAuthError(w, business.Code)
			return
		}
		writeError(w, 502, "認証サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if operation == "login" {
		expires, _ := time.Parse(time.RFC3339, result.ExpiresAt)
		h.cookie(w, result.SessionToken, expires, max(1, int(time.Until(expires).Seconds())))
	}
	if operation == "logout" {
		h.cookie(w, "", time.Time{}, -1)
	}
	result.SessionToken = "" // Cookie以外でセッション原値を公開しない。
	status := 200
	if operation == "register" {
		status = 201
	}
	writeJSON(w, status, result)
}
func writeAuthError(w http.ResponseWriter, code string) {
	status, detail := 503, "認証処理を利用できません。時間をおいて再試行してください。"
	switch code {
	case "invalid_username":
		status, detail = 422, "ユーザー名は半角英数字・アンダースコアの3〜32文字で入力してください。"
	case "invalid_password":
		status, detail = 422, "パスワードの文字数が設定された範囲外です。"
	case "invalid_recovery":
		status, detail = 400, "ユーザー名または復旧コードを確認してください。"
	case "invalid_credentials":
		status, detail = 401, "ユーザー名またはパスワードを確認してください。"
	case "invalid_csrf":
		status, detail = 403, "操作を確認できません。画面を再読み込みしてください。"
	case "rate_limited":
		status, detail = 429, "試行回数の上限に達しました。時間をおいて再試行してください。"
	case "registration_conflict":
		status, detail = 409, "このユーザー名は使用されています。別のユーザー名を指定してください。"
	}
	writeError(w, status, detail)
}
