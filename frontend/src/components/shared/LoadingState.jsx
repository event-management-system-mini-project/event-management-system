
import React from "react";

/**
 * Reusable accessible loading indicator.
 *
 * Props:
 * - message (string): Text announced while the content loads.
 * - className (string): Optional CSS class for local styling.
 *
 * Example:
 * <LoadingState message="Loading upcoming events..." />
 */
export default function LoadingState({
  message = "Loading...",
  className = "",
}) {
  return (
    <p
      className={["shared-loading", className].filter(Boolean).join(" ")}
      role="status"
      aria-live="polite"
    >
      {message}
    </p>
  );
}
