import { useEffect } from "react";
import type { PropsWithChildren, ReactNode } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeClasses = {
  sm: "max-w-md",
  md: "max-w-xl",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

export function Modal({
  open,
  onClose,
  title,
  description,
  footer,
  size = "md",
  children,
}: PropsWithChildren<ModalProps>): ReactNode {
  const isBrowser = typeof document !== "undefined";
  const container = isBrowser ? document.body : null;

  useEffect(() => {
    if (!open || !isBrowser) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose, isBrowser]);

  if (!isBrowser || !open || !container) {
    return null;
  }

  const content = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      onMouseDown={onClose}
      role="presentation"
    >
      <div
        className={cn(
          "relative w-full rounded-lg border border-border bg-card shadow-xl",
          sizeClasses[size],
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        aria-describedby={description ? "modal-description" : undefined}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex flex-col gap-4 p-6">
          <header className="space-y-1">
            {title ? (
              <h2 id="modal-title" className="text-lg font-semibold">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p id="modal-description" className="text-sm text-muted-foreground">
                {description}
              </p>
            ) : null}
          </header>
          <div className="max-h-[70vh] overflow-y-auto pr-1 text-sm">{children}</div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border bg-muted/20 px-6 py-3">
          {footer}
        </div>
        <button
          type="button"
          className="absolute right-4 top-4 rounded-md border border-border/60 bg-background px-2 py-1 text-xs font-medium text-muted-foreground transition hover:bg-muted"
          onClick={onClose}
        >
          Fechar
        </button>
      </div>
    </div>
  );

  return createPortal(content, container);
}
