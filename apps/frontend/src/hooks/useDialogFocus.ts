import { useEffect, useRef, type RefObject } from "react";

// Shared by modal windows and the mobile menu. Only the active dialog is interactive.
export function useDialogFocus(
  panel: RefObject<HTMLElement | null>,
  open: boolean,
  onClose: () => void,
) {
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const element = panel.current;
    if (!open || !element) return;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const blocked: Array<{ element: HTMLElement; inert: boolean }> = [];
    // Mark siblings along the ancestor path, so routed modals can live inside main.
    let current: HTMLElement = element;
    while (current.parentElement) {
      for (const sibling of current.parentElement.children) {
        if (sibling !== current && sibling instanceof HTMLElement) {
          blocked.push({ element: sibling, inert: sibling.inert });
          sibling.setAttribute("inert", "");
        }
      }
      current = current.parentElement;
      if (current === document.body) break;
    }
    document.body.style.overflow = "hidden";
    element.focus({ preventScroll: true });
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close.current();
      }
      if (event.key !== "Tab") return;
      const elements = [
        ...element.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href], [tabindex="0"]',
        ),
      ].filter(
        (item) => item.getClientRects().length && !item.closest("[inert]"),
      );
      if (!elements.length) {
        event.preventDefault();
        return;
      }
      const first = elements[0];
      const last = elements[elements.length - 1];
      const outside = !element.contains(document.activeElement);
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          document.activeElement === element ||
          outside)
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          document.activeElement === element ||
          outside)
      ) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      blocked.forEach((item) => {
        item.element.toggleAttribute("inert", item.inert);
      });
      document.removeEventListener("keydown", handleKey);
      if (
        previousFocus instanceof HTMLElement &&
        previousFocus.isConnected &&
        !previousFocus.closest("[inert]")
      ) {
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, [open, panel]);
}
