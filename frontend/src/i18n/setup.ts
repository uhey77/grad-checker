import { createSiteI18n } from "./createI18n.ts";

let storage: Storage | undefined;
try {
  storage = window.localStorage;
} catch {
  /* 保存が制限されたブラウザーでも起動する。 */
}
export const siteI18n = createSiteI18n({
  storage,
  languages: navigator.languages.length
    ? navigator.languages
    : [navigator.language],
  page: document,
});
