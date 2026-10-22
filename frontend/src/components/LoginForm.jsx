import React, { useId, useState } from "react";

export default function LoginForm({ onLogin }) {
  const fieldId = useId();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    const nextErrors = {};
    if (!username.trim()) nextErrors.username = ["Enter your username."];
    if (!password) nextErrors.password = ["Enter your password."];
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setBusy(true);
    try {
      await onLogin(username.trim(), password);
    } catch (error) {
      if (error.fields) setErrors(error.fields);
      else setFormError(error.message || "Sign in failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const usernameError = errors.username?.[0];
  const passwordError = errors.password?.[0];

  return (
    <section className="auth-panel" aria-labelledby="login-heading">
      <p className="eyebrow">Organizer access</p>
      <h1 id="login-heading">Sign in to manage your events</h1>
      <p className="lede">
        Use the organizer account created for this local environment. Your
        session is verified by the server, not by the browser.
      </p>

      <form className="form-stack" onSubmit={handleSubmit} noValidate>
        {formError ? (
          <p className="form-alert" role="alert">
            {formError}
          </p>
        ) : null}

        <div className="field">
          <label htmlFor={`${fieldId}-username`}>Username</label>
          <input
            id={`${fieldId}-username`}
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            aria-invalid={usernameError ? "true" : undefined}
            aria-describedby={usernameError ? `${fieldId}-username-error` : undefined}
          />
          {usernameError ? (
            <p className="field-error" id={`${fieldId}-username-error`}>
              {usernameError}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label htmlFor={`${fieldId}-password`}>Password</label>
          <input
            id={`${fieldId}-password`}
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={passwordError ? "true" : undefined}
            aria-describedby={passwordError ? `${fieldId}-password-error` : undefined}
          />
          {passwordError ? (
            <p className="field-error" id={`${fieldId}-password-error`}>
              {passwordError}
            </p>
          ) : null}
        </div>

        <button className="button" type="submit" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </section>
  );
}
