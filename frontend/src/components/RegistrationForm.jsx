import React, { useId, useState } from "react";
import * as defaultApi from "../api.js";

export default function RegistrationForm({ eventId, onRegistered, api = defaultApi }) {
  const fieldId = useId();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess(false);
    setBusy(true);

    try {
      const data = await api.registerForEvent(eventId, { name: name.trim(), email: email.trim() });

      setSuccess(true);
      setName("");
      setEmail("");
      if (onRegistered) onRegistered(data);
    } catch (err) {
      setError(err.fields?.email?.[0] || err.message || "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="form-stack" onSubmit={handleSubmit}>
      {error ? <p className="form-alert" role="alert">{error}</p> : null}
      {success ? <p className="form-success" role="status">Successfully registered!</p> : null}

      <div className="field">
        <label htmlFor={`${fieldId}-reg-name`}>Your Name</label>
        <input
          id={`${fieldId}-reg-name`}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          disabled={busy}
        />
      </div>

      <div className="field">
        <label htmlFor={`${fieldId}-reg-email`}>Your Email</label>
        <input
          id={`${fieldId}-reg-email`}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={254}
          disabled={busy}
        />
      </div>

      <button className="button" type="submit" disabled={busy}>
        {busy ? "Registering..." : "Register for Event"}
      </button>
    </form>
  );
}
