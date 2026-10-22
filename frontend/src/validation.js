export const NAME_LIMIT = 100;
export const DESCRIPTION_LIMIT = 1000;

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

function parseLocalDateTime(date, time) {
  const dateParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const timeParts = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(time);
  if (!dateParts || !timeParts) return null;

  const year = Number(dateParts[1]);
  const month = Number(dateParts[2]);
  const day = Number(dateParts[3]);
  const hour = Number(timeParts[1]);
  const minute = Number(timeParts[2]);
  const second = timeParts[3] === undefined ? 0 : Number(timeParts[3]);
  const value = new Date(year, month - 1, day, hour, minute, second, 0);
  if (
    value.getFullYear() !== year ||
    value.getMonth() !== month - 1 ||
    value.getDate() !== day ||
    value.getHours() !== hour ||
    value.getMinutes() !== minute ||
    value.getSeconds() !== second
  ) {
    return null;
  }
  return value;
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
    const startsAt = parseLocalDateTime(values.date, values.time);
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
