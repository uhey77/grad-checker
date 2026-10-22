import { useTranslation } from "react-i18next";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  return (
    <label className="language-switcher">
      <span>{t("言語")}</span>
      <select
        aria-label={t("言語")}
        value={i18n.resolvedLanguage ?? "ja"}
        onChange={(event) => {
          void i18n.changeLanguage(event.target.value);
        }}
      >
        <option value="ja" lang="ja">
          日本語
        </option>
        <option value="en" lang="en">
          English
        </option>
      </select>
    </label>
  );
}
