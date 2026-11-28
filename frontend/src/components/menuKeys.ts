import type { KeyboardEvent } from "react";

// Arrow, Home/End and Escape handling shared by the header dropdown menus.
export function onMenuKeyDown(
  event: KeyboardEvent<HTMLDivElement>,
  close: (restoreFocus: boolean) => void
) {
  const items = Array.from(
    event.currentTarget.querySelectorAll<HTMLElement>("[role=menuitem]")
  );
  const current = items.indexOf(document.activeElement as HTMLElement);
  if (event.key === "Escape") {
    event.preventDefault();
    close(true);
  }
  if (
    event.key === "ArrowDown" ||
    event.key === "ArrowUp" ||
    event.key === "Home" ||
    event.key === "End"
  ) {
    event.preventDefault();
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) %
            items.length;
    items[next]?.focus();
  }
}
