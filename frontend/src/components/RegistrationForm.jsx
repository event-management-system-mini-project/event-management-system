import React, { useId, useState } from "react";

export default function RegistrationForm({ eventId, onRegistered }) {
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
      const response = await fetch(`/api/events/${eventId}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email }),
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw data;
      }

      setSuccess(true);
      setName("");
      setEmail("");
      if (onRegistered) onRegistered(data);
    } catch (err) {
      setError(err.detail || err.fields?.email?.[0] || "Registration failed.");
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
        />
      </div>

      <button className="button" type="submit" disabled={busy}>
        {busy ? "Registering..." : "Register for Event"}
      </button>
    </form>
  );
}