import { useTranslation } from "react-i18next";
import { HeaderButton } from "./HeaderButton.tsx";

export function ProfileButton({ showProfile }: { showProfile: () => void }) {
  const { t } = useTranslation();
  return (
    <HeaderButton
      aria-label={t("マイページ")}
      title={t("マイページ")}
      onClick={showProfile}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
      </svg>
    </HeaderButton>
  );
}
