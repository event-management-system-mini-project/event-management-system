
import React from "react";

/**
 * Reusable accessible success message.
 *
 * Props:
 * - message (string): Success text.
 * - className (string): Optional styling class.
 */
export default function SuccessState({
  message = "Your action was completed successfully.",
  className = "",
}) {
  return (
    <p
      className={["shared-success", className]
        .filter(Boolean)
        .join(" ")}
      role="status"
      aria-live="polite"
    >
      {message}
    </p>
  );
}
