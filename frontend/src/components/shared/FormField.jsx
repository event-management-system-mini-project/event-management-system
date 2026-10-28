
import React, { useId } from "react";

/**
 * Props:
 * - label: Required visible label.
 * - name: Input name.
 * - type: Input type.
 * - value: Controlled input value.
 * - onChange: Input change callback.
 * - required: Whether a value is required.
 * - error: Optional validation message.
 * - hint: Optional helper text.
 */
export default function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  required = false,
  error = "",
  hint = "",
  ...props
}) {
  const generatedId = useId();
  const inputId = props.id || `${name || "field"}-${generatedId}`;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  return (
    <div className="shared-form-field">
      <label htmlFor={inputId}>
        {label}
        {required ? " *" : ""}
      </label>

      <input
        {...props}
        id={inputId}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        aria-invalid={Boolean(error)}
        aria-describedby={[
          hint ? hintId : "",
          error ? errorId : "",
        ].filter(Boolean).join(" ") || undefined}
      />

      {hint ? <p id={hintId}>{hint}</p> : null}
      {error ? <p id={errorId} role="alert">{error}</p> : null}
    </div>
  );
}
