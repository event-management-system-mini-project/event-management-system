
import React from "react";

/**
 * Props:
 * - children: Button text or content.
 * - type: "button", "submit", or "reset".
 * - variant: Optional styling variant.
 * - disabled: Disables interaction.
 * - loading: Shows a busy label and prevents repeat submissions.
 * - loadingLabel: Text shown while loading.
 */
export default function SharedButton({
  children,
  type = "button",
  variant = "primary",
  disabled = false,
  loading = false,
  loadingLabel = "Please wait...",
  className = "",
  ...props
}) {
  const classes = [
    "button",
    `button-${variant}`,
    className,
  ].filter(Boolean).join(" ");

  return (
    <button
      {...props}
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading ? loadingLabel : children}
    </button>
  );
}
