import { Sidebar } from "./Sidebar";

export function MobileDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <div
      id="mobile-menu"
      className={`mobile-drawer ${open ? "is-open" : ""}`}
      inert={!open}
      aria-hidden={!open}
    >
      <div className="drawer-backdrop" onClick={onClose} />
      <Sidebar variant="drawer" onNavigate={onClose} />
    </div>
  );
}
