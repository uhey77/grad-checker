// 一覧の検索・絞り込み欄。選択肢は[値, 表示名]で受け取る。

export function SearchField({
  id,
  label,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="search-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="search"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

export function FilterSelect({
  id,
  label,
  value,
  options,
  allLabel = "すべて",
  disabled = false,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: (readonly [string, string])[];
  // 絞り込まない選択肢の表示名。nullの場合は設けない（並べ替えなど）。
  allLabel?: string | null;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {allLabel === null ? null : <option value="">{allLabel}</option>}
        {options.map(([optionValue, text]) => (
          <option key={optionValue} value={optionValue}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}
