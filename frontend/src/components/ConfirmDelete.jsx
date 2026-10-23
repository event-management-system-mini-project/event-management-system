import React, { useEffect, useRef } from "react";

export default function ConfirmDelete({
  event,
  busy,
  error,
  onCancel,
  onConfirm,
}) {
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
    function handleKeyDown(keyEvent) {
      if (keyEvent.key === "Escape" && !busy) onCancel();
    }
    globalThis.document?.addEventListener("keydown", handleKeyDown);
    return () => {
      globalThis.document?.removeEventListener("keydown", handleKeyDown);
    };
  }, [busy, onCancel]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(mouseEvent) => {
        if (mouseEvent.target === mouseEvent.currentTarget && !busy) onCancel();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-heading"
        aria-describedby="delete-description"
      >
        <p className="eyebrow">Delete event</p>
        <h2 id="delete-heading">Delete “{event.name}”?</h2>
        <p className="modal-body" id="delete-description">
          This removes the event and all of its registrations. This cannot be
          undone.
        </p>

        {error ? (
          <p className="form-alert" role="alert">
            {error}
          </p>
        ) : null}

        <div className="form-actions">
          <button
            className="button danger"
            type="button"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? "Deleting..." : "Delete event"}
          </button>
          <button
            className="button secondary"
            type="button"
            onClick={onCancel}
            disabled={busy}
            ref={cancelRef}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
