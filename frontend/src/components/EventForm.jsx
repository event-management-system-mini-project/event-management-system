import React, { useId, useState } from "react";

import {
  DESCRIPTION_LIMIT,
  NAME_LIMIT,
  hasErrors,
  normalizedEventValues,
  validateEvent,
} from "../validation.js";

const EMPTY_VALUES = {
  name: "",
  description: "",
  date: "",
  time: "",
  location: "",
};

function todayIso() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${today.getFullYear()}-${month}-${day}`;
}

function characterCount(value) {
  return [...value.trim()].length;
}

export default function EventForm({ onCreate, onSessionExpired }) {
  const fieldId = useId();
  const [values, setValues] = useState(EMPTY_VALUES);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [savedName, setSavedName] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
    setSavedName("");
  }

  function focusFirstError(nextErrors) {
    const first = ["name", "description", "date", "time", "location"].find(
      (field) => nextErrors[field],
    );
    if (first) globalThis.document?.getElementById(`${fieldId}-${first}`)?.focus();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setSavedName("");

    const nextErrors = validateEvent(values);
    setErrors(nextErrors);
    if (hasErrors(nextErrors)) {
      focusFirstError(nextErrors);
      return;
    }

    setBusy(true);
    try {
      const saved = await onCreate(normalizedEventValues(values));
      setValues(EMPTY_VALUES);
      setErrors({});
      setSavedName(saved.name);
    } catch (error) {
      if (error.status === 401) {
        onSessionExpired();
        return;
      }
      if (error.fields) {
        setErrors(error.fields);
        focusFirstError(error.fields);
      } else {
        setFormError(
          error.message || "The event could not be saved. Nothing was confirmed.",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  const nameError = errors.name?.[0];
  const descriptionError = errors.description?.[0];
  const dateError = errors.date?.[0];
  const timeError = errors.time?.[0];
  const locationError = errors.location?.[0];

  return (
    <section className="panel" aria-labelledby="create-heading">
      <div className="panel-heading">
        <p className="eyebrow">New event</p>
        <h2 id="create-heading">Create an event</h2>
        <p className="panel-intro">
          Save the details once. The event appears in your list after the database
          confirms the write.
        </p>
      </div>

      <form className="form-stack" onSubmit={handleSubmit} noValidate>
        {formError ? (
          <p className="form-alert" role="alert">
            {formError}
          </p>
        ) : null}
        {savedName ? (
          <p className="form-success" role="status">
            Saved “{savedName}”. It is now in your event list.
          </p>
        ) : null}

        <div className="field">
          <div className="label-row">
            <label htmlFor={`${fieldId}-name`}>Event name</label>
            <span className="counter" aria-hidden="true">
              {characterCount(values.name)}/{NAME_LIMIT}
            </span>
          </div>
          <input
            id={`${fieldId}-name`}
            name="name"
            value={values.name}
            onChange={(event) => update("name", event.target.value)}
            aria-invalid={nameError ? "true" : undefined}
            aria-describedby={`${fieldId}-name-hint${nameError ? ` ${fieldId}-name-error` : ""}`}
          />
          <p className="hint" id={`${fieldId}-name-hint`}>
            Between 1 and {NAME_LIMIT} characters.
          </p>
          {nameError ? (
            <p className="field-error" id={`${fieldId}-name-error`}>
              {nameError}
            </p>
          ) : null}
        </div>

        <div className="field">
          <div className="label-row">
            <label htmlFor={`${fieldId}-description`}>Description</label>
            <span className="counter" aria-hidden="true">
              {characterCount(values.description)}/{DESCRIPTION_LIMIT}
            </span>
          </div>
          <textarea
            id={`${fieldId}-description`}
            name="description"
            rows={4}
            value={values.description}
            onChange={(event) => update("description", event.target.value)}
            aria-invalid={descriptionError ? "true" : undefined}
            aria-describedby={`${fieldId}-description-hint${descriptionError ? ` ${fieldId}-description-error` : ""}`}
          />
          <p className="hint" id={`${fieldId}-description-hint`}>
            Up to 1,000 characters.
          </p>
          {descriptionError ? (
            <p className="field-error" id={`${fieldId}-description-error`}>
              {descriptionError}
            </p>
          ) : null}
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor={`${fieldId}-date`}>Date</label>
            <input
              id={`${fieldId}-date`}
              name="date"
              type="date"
              min={todayIso()}
              value={values.date}
              onChange={(event) => update("date", event.target.value)}
              aria-invalid={dateError ? "true" : undefined}
              aria-describedby={dateError ? `${fieldId}-date-error` : undefined}
            />
            {dateError ? (
              <p className="field-error" id={`${fieldId}-date-error`}>
                {dateError}
              </p>
            ) : null}
          </div>

          <div className="field">
            <label htmlFor={`${fieldId}-time`}>Start time (IST)</label>
            <input
              id={`${fieldId}-time`}
              name="time"
              type="time"
              value={values.time}
              onChange={(event) => update("time", event.target.value)}
              aria-invalid={timeError ? "true" : undefined}
              aria-describedby={timeError ? `${fieldId}-time-error` : undefined}
            />
            {timeError ? (
              <p className="field-error" id={`${fieldId}-time-error`}>
                {timeError}
              </p>
            ) : null}
          </div>
        </div>

        <div className="field">
          <label htmlFor={`${fieldId}-location`}>Location</label>
          <input
            id={`${fieldId}-location`}
            name="location"
            value={values.location}
            onChange={(event) => update("location", event.target.value)}
            aria-invalid={locationError ? "true" : undefined}
            aria-describedby={locationError ? `${fieldId}-location-error` : undefined}
          />
          {locationError ? (
            <p className="field-error" id={`${fieldId}-location-error`}>
              {locationError}
            </p>
          ) : null}
        </div>

        <button className="button" type="submit" disabled={busy}>
          {busy ? "Saving..." : "Create event"}
        </button>
      </form>
    </section>
  );
}
