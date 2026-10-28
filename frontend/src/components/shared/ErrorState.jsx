
import React from "react";

/**
 * Reusable accessible error message.
 *
 * Props:
 * - message (string): Error text to display.
 * - onRetry (function, optional): Called when Retry is clicked.
 * - retryLabel (string): Accessible retry button text.
 */
export default function ErrorState({
  message = "Something went wrong.",
  onRetry,
  retryLabel = "Try again",
}) {
  return (
    <div className="shared-error" role="alert">
      <p>{message}</p>

      {onRetry ? (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
