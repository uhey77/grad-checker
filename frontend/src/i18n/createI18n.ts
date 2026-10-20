import { createInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import { english } from "./en.ts";

export type Language = "ja" | "en";
export const languageStorageKey = "grad-checker.language.v1";
type LanguageStorage = Pick<Storage, "getItem" | "setItem">;

export function initialLanguage(
  stored: string | null,
  languages: readonly string[],
): Language {
  if (stored === "ja" || stored === "en") return stored;
  for (const language of languages) {
    const base = language.toLowerCase().split(/[-_]/)[0];
    if (base === "ja" || base === "en") return base;
  }
  return "ja";
}

export function createSiteI18n({
  storage,
  languages = [],
  page,
}: {
  storage?: LanguageStorage;
  languages?: readonly string[];
  page?: Pick<Document, "documentElement" | "title">;
} = {}) {
  let stored: string | null = null;
  try {
    stored = storage?.getItem(languageStorageKey) ?? null;
  } catch {
    /* 保存不可でも切替は利用できる。 */
  }
  const instance = createInstance();
  void instance.use(initReactI18next).init({
    resources: {
      ja: {
        translation: Object.fromEntries(
          Object.keys(english).map((key) => [key, key]),
        ),
      },
      en: { translation: english },
    },
    lng: initialLanguage(stored, languages),
    supportedLngs: ["ja", "en"],
    fallbackLng: "ja",
    keySeparator: false,
    nsSeparator: false,
    initAsync: false,
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
  });
  const updatePage = () => {
    if (!page) return;
    page.documentElement.lang = instance.resolvedLanguage ?? "ja";
    page.title = instance.t("卒業要件チェッカー");
  };
  updatePage();
  instance.on("languageChanged", (language) => {
    updatePage();
    // 選択された言語だけを保存し、認証情報や入力内容は保存しない。
    try {
      storage?.setItem(languageStorageKey, language);
    } catch {
      /* メモリー上では切替を継続する。 */
    }
  });
  return instance;
}
