// APIのJSONを実行時に検証して読む共通処理。不正な値は呼出し側の業務エラーへ変換する。
export function createDtoReader(invalid: () => never) {
  function record(value: unknown): Record<string, unknown> {
    if (!value || typeof value !== "object" || Array.isArray(value))
      return invalid();
    return value as Record<string, unknown>;
  }
  function list(value: unknown): unknown[] {
    return Array.isArray(value) ? value : invalid();
  }
  function text(value: unknown): string {
    if (typeof value !== "string" || !value.trim()) return invalid();
    return value;
  }
  function nullableText(value: unknown): string | null {
    return value === null ? null : text(value);
  }
  function integer(value: unknown, minimum = 0): number {
    if (
      typeof value !== "number" ||
      !Number.isSafeInteger(value) ||
      value < minimum
    )
      return invalid();
    return value;
  }
  function nullableInteger(value: unknown, minimum = 1): number | null {
    return value === null ? null : integer(value, minimum);
  }
  return {
    invalid,
    record,
    list,
    text,
    nullableText,
    integer,
    nullableInteger,
  };
}
