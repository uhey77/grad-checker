import type { ComponentProps } from "react";

export function HeaderButton(
  props: Omit<ComponentProps<"button">, "type" | "className">,
) {
  return <button {...props} type="button" className="header-button" />;
}
