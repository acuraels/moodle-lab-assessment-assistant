import { useEffect, useRef, useState } from "react";
import { Icon } from "../ui/Icon";
import { MobileDrawer } from "./MobileDrawer";
import { useDialogFocus } from "../../hooks/useDialogFocus";

export function MobileHeader() {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);
  useDialogFocus(dialog, open, () => setOpen(false));
  useEffect(() => {
    const close = () => setOpen(false);
    window.addEventListener("popstate", close);
    return () => window.removeEventListener("popstate", close);
  }, []);
  return (
    <div
      ref={dialog}
      className="mobile-navigation"
      role={open ? "dialog" : undefined}
      aria-modal={open ? true : undefined}
      aria-label={open ? "Навигация" : undefined}
      tabIndex={-1}
    >
      <header className="mobile-header">
        <button
          className="icon-button menu-toggle"
          aria-label={open ? "Закрыть меню" : "Открыть меню"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((value) => !value)}
        >
          <Icon name={open ? "close" : "menu"} size={24} />
        </button>
        <span className="mobile-brand">
          лаб<span>.ai</span>
        </span>
        <span className="mobile-context">Лабораторная № 3</span>
      </header>
      <MobileDrawer open={open} onClose={() => setOpen(false)} />
    </div>
  );
}
