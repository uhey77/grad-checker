// Package internalhttpは、各業務モジュールのinfrastructureがPython内部サービスを呼ぶ共通処理。
// 内部通信の包絡形式 {"data": ...} / {"error": {"code": ...}} をこのパッケージに閉じ込める。
// 業務エラーの型への変換と、dataの業務上の検証は呼出し側のモジュールで行う。
package internalhttp

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"net/url"
	"time"
)

var (
	ErrUnavailable = errors.New("internal service unavailable")
	ErrTimeout     = errors.New("internal service timeout")
	ErrProtocol    = errors.New("invalid internal response")
)

// BusinessErrorはPythonのユースケースが返した業務エラーコード。
type BusinessError struct {
	Code string
}

func (e *BusinessError) Error() string { return e.Code }

type Client struct {
	endpoint string
	client   *http.Client
	limit    int64
}

// NewはPython内部サービスのオリジンとパスから取得先を作る。limitは応答本文の上限バイト数。
func New(origin, path string, timeout time.Duration, limit int64) (*Client, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("python-urlにはパスを含まないhttp/httpsオリジンを指定してください。")
	}
	return &Client{
		endpoint: origin + path,
		client:   &http.Client{Timeout: timeout, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }},
		limit:    limit,
	}, nil
}

// Callは操作をJSONで送り、成功時のdataを返す。業務エラーは*BusinessError、
// 通信失敗はErrUnavailable・ErrTimeout、包絡形式の違反はErrProtocolを返す。
func (c *Client) Call(ctx context.Context, call any) (json.RawMessage, error) {
	payload, err := json.Marshal(call)
	if err != nil {
		return nil, ErrProtocol
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, ErrUnavailable
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := c.client.Do(request)
	if err != nil {
		var timeout net.Error
		if errors.Is(err, context.DeadlineExceeded) || (errors.As(err, &timeout) && timeout.Timeout()) {
			return nil, ErrTimeout
		}
		return nil, ErrUnavailable
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, ErrProtocol
	}
	// 包絡の項目は厳格に確認し、業務エラーはコードだけを読む。付加情報（SQLの詳細など）は外部へ渡さない。
	var envelope struct {
		Data  json.RawMessage `json:"data"`
		Error json.RawMessage `json:"error"`
	}
	if DecodeStrict(io.LimitReader(response.Body, c.limit), &envelope) != nil {
		return nil, ErrProtocol
	}
	data := bytes.TrimSpace(envelope.Data)
	hasData := len(data) != 0 && string(data) != "null"
	failed := bytes.TrimSpace(envelope.Error)
	if len(failed) != 0 && string(failed) != "null" {
		var failure struct {
			Code string `json:"code"`
		}
		if hasData || json.Unmarshal(failed, &failure) != nil || failure.Code == "" {
			return nil, ErrProtocol
		}
		return nil, &BusinessError{failure.Code}
	}
	if !hasData {
		return nil, ErrProtocol
	}
	return data, nil
}

// DecodeStrictは未知の項目と末尾の余分な値を拒否してJSONを読む。
func DecodeStrict(source io.Reader, value any) error {
	decoder := json.NewDecoder(source)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(value); err != nil {
		return err
	}
	var trailing any
	if decoder.Decode(&trailing) != io.EOF {
		return ErrProtocol
	}
	return nil
}

// DecodeDataはdataを未知の項目なしで読む。
func DecodeData(data json.RawMessage, value any) error {
	return DecodeStrict(bytes.NewReader(data), value)
}
