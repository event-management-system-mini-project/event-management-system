
import React from "react";

/**
 * Reusable empty-results message.
 *
 * Props:
 * - title (string): Short heading.
 * - message (string): Explanation shown to the user.
 * - action (ReactNode, optional): Optional action such as a button.
 */
export default function EmptyState({
  title = "Nothing here yet",
  message = "There is no content to display.",
  action = null,
}) {
  return (
    <section className="shared-empty" aria-label={title}>
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </section>
  );
}
