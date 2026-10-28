export const NAME_LIMIT = 100;
export const DESCRIPTION_LIMIT = 1000;
export const EVENT_TIME_ZONE = "Asia/Kolkata";
export const EVENT_UTC_OFFSET_MINUTES = 5 * 60 + 30;

const EVENT_UTC_OFFSET_MS = EVENT_UTC_OFFSET_MINUTES * 60 * 1000;

export function normalizedEventValues(values) {
  return {
    name: values.name.trim(),
    description: values.description.trim(),
    date: values.date,
    time: values.time,
    location: values.location.trim(),
  };
}

function textLength(value) {
  return [...value.trim()].length;
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

/**
 * Interpret a date/time entered in the organizer form as Asia/Kolkata time.
 *
 * The contract timezone has a fixed UTC+05:30 offset and no daylight-saving
 * transition, so the conversion is deterministic in every browser timezone.
 * The UTC components are checked after construction to reject impossible
 * values such as 2030-02-31 or 24:00.
 */
function parseEventDateTime(date, time) {
  const dateParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const timeParts = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(time);
  if (!dateParts || !timeParts) return null;

  const year = Number(dateParts[1]);
  const month = Number(dateParts[2]);
  const day = Number(dateParts[3]);
  const hour = Number(timeParts[1]);
  const minute = Number(timeParts[2]);
  const second = timeParts[3] === undefined ? 0 : Number(timeParts[3]);

  const istComponents = new Date(0);
  istComponents.setUTCFullYear(year, month - 1, day);
  istComponents.setUTCHours(hour, minute, second, 0);
  if (
    istComponents.getUTCFullYear() !== year ||
    istComponents.getUTCMonth() !== month - 1 ||
    istComponents.getUTCDate() !== day ||
    istComponents.getUTCHours() !== hour ||
    istComponents.getUTCMinutes() !== minute ||
    istComponents.getUTCSeconds() !== second
  ) {
    return null;
  }

  return new Date(istComponents.getTime() - EVENT_UTC_OFFSET_MS);
}

/**
 * Earliest date selectable in the IST calendar for a given instant.
 *
 * This is deliberately independent of the browser's local timezone so a user
 * in Los Angeles still sees the same earliest date as the server contract.
 */
export function earliestSelectableDate(now = new Date()) {
  const istNow = new Date(now.getTime() + EVENT_UTC_OFFSET_MS);
  const year = istNow.getUTCFullYear();
  const month = pad2(istNow.getUTCMonth() + 1);
  const day = pad2(istNow.getUTCDate());
  return `${year}-${month}-${day}`;
}

/** Return field -> messages, mirroring the server's validation rules. */
export function validateEvent(values, now = new Date()) {
  const errors = {};
  const name = values.name.trim();
  const description = values.description.trim();
  const location = values.location.trim();

  if (!name) errors.name = ["Enter an event name."];
  else if (textLength(name) > NAME_LIMIT) {
    errors.name = [`Use ${NAME_LIMIT} characters or fewer.`];
  }

  if (!description) errors.description = ["Add a description."];
  else if (textLength(description) > DESCRIPTION_LIMIT) {
    errors.description = ["Use 1,000 characters or fewer."];
  }

  if (!location) errors.location = ["Add a location."];

  if (!values.date) {
    errors.date = ["Choose a date."];
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(values.date)) {
    errors.date = ["Use the YYYY-MM-DD format."];
  }

  if (!values.time) {
    errors.time = ["Choose a time."];
  } else if (!/^\d{2}:\d{2}(?::\d{2})?$/.test(values.time)) {
    errors.time = ["Use the HH:MM format."];
  }

  if (values.date && values.time && !errors.date && !errors.time) {
    const startsAt = parseEventDateTime(values.date, values.time);
    if (!startsAt) {
      errors.date = ["Choose a valid date and time."];
    } else if (startsAt <= now) {
      errors.date = ["Choose a date and time in the future."];
    }
  }

  return errors;
}

export function hasErrors(errors) {
  return Object.keys(errors).length > 0;
}
