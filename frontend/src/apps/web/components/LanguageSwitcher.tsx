import { useTranslation } from "react-i18next";

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const targetLanguage = i18n.resolvedLanguage === "en" ? "ja" : "en";
  const label =
    targetLanguage === "ja" ? "日本語に切り替える" : "Switch to English";

  return (
    <button
      type="button"
      className="language-switcher"
      lang={targetLanguage}
      aria-label={label}
      title={label}
      onClick={() => {
        void i18n.changeLanguage(targetLanguage);
      }}
    >
      {targetLanguage.toUpperCase()}
    </button>
  );
}
