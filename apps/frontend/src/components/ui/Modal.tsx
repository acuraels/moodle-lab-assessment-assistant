import { useRef, type ReactNode } from "react";
import { useDialogFocus } from "../../hooks/useDialogFocus";

export function Modal({
  children,
  onClose,
  titleId,
  className = "",
}: {
  children: ReactNode;
  onClose: () => void;
  titleId: string;
  className?: string;
}) {
  const panel = useRef<HTMLElement>(null);
  useDialogFocus(panel, true, onClose);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <section
        ref={panel}
        className={`modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </section>
    </div>
  );
}
