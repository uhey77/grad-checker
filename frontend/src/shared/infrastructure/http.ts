// 業務モジュールのinfrastructureが共通で使うHTTP通信。業務固有のエラー契約や文言は呼出し側が決める。

export interface JsonRequest {
  method?: "GET" | "POST" | "PUT";
  payload?: object;
  // 更新系の要求で送るCSRFトークン。指定した場合だけヘッダーに付ける。
  csrf?: string;
  signal?: AbortSignal;
}

export interface JsonResponse {
  ok: boolean;
  status: number;
  data: unknown;
}

// 通信できなかった、または応答がJSONでなかった失敗。キャンセルはこの型へ変換しない。
export class HttpTransportError extends Error {
  constructor(
    readonly kind: "network" | "invalid-json",
    readonly status: number,
    readonly ok: boolean,
    options?: ErrorOptions,
  ) {
    super(kind, options);
    this.name = "HttpTransportError";
  }
}

function cancelled(error: unknown, signal?: AbortSignal): boolean {
  return (
    !!signal?.aborted ||
    (error instanceof DOMException && error.name === "AbortError")
  );
}

// 同一オリジンのCookieを送り、キャッシュを使わずにJSONを取得する。HTTPステータスの判断は呼出し側で行う。
export async function fetchJson(
  url: string,
  { method, payload, csrf, signal }: JsonRequest = {},
): Promise<JsonResponse> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: method ?? (payload ? "POST" : "GET"),
      credentials: "same-origin",
      cache: "no-store",
      signal,
      headers: payload
        ? {
            "Content-Type": "application/json",
            ...(csrf === undefined ? {} : { "X-CSRF-Token": csrf }),
          }
        : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
    });
  } catch (error) {
    if (cancelled(error, signal)) throw error;
    throw new HttpTransportError("network", 0, false, { cause: error });
  }
  try {
    return {
      ok: response.ok,
      status: response.status,
      data: await response.json(),
    };
  } catch (error) {
    if (cancelled(error, signal)) throw error;
    throw new HttpTransportError("invalid-json", response.status, response.ok, {
      cause: error,
    });
  }
}

// エラー応答の日本語detail。形式が異なる場合はnull。
export function detailOf(data: unknown): string | null {
  return data &&
    typeof data === "object" &&
    "detail" in data &&
    typeof data.detail === "string"
    ? data.detail
    : null;
}

export interface StatusErrorMessages {
  // 成功応答がJSONでない場合。
  unreadable: string;
  // エラー応答がJSONでない場合。省略時はunreadable。
  unreadableFailure?: string;
  // エラー応答にdetailがない場合。
  failed: string;
}

export const unreachableMessage =
  "サーバーへ接続できません。時間をおいて再試行してください。";

// HTTPステータス（通信失敗は0、成功時の不正応答は502）と日本語の文言で業務エラーを作る取得先向け。
export async function requestJson(
  url: string,
  request: JsonRequest,
  createError: (status: number, message: string) => Error,
  messages: StatusErrorMessages,
): Promise<unknown> {
  let response: JsonResponse;
  try {
    response = await fetchJson(url, request);
  } catch (error) {
    if (!(error instanceof HttpTransportError)) throw error;
    if (error.kind === "network") throw createError(0, unreachableMessage);
    throw error.ok
      ? createError(502, messages.unreadable)
      : createError(
          error.status,
          messages.unreadableFailure ?? messages.unreadable,
        );
  }
  if (!response.ok)
    throw createError(
      response.status,
      detailOf(response.data) ?? messages.failed,
    );
  return response.data;
}
