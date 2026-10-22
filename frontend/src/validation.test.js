import { describe, expect, it } from "vitest";

import {
  DESCRIPTION_LIMIT,
  NAME_LIMIT,
  normalizedEventValues,
  validateEvent,
} from "./validation.js";

const NOW = new Date(2030, 0, 1, 12, 0, 0);

function values(changes = {}) {
  return {
    name: "Synthetic Workshop",
    description: "A synthetic event for validation tests.",
    date: "2030-02-01",
    time: "10:00",
    location: "Synthetic Hall",
    ...changes,
  };
}

describe("validateEvent", () => {
  it("accepts a valid future event", () => {
    expect(validateEvent(values(), NOW)).toEqual({});
  });

  it("enforces the 100-character name boundary", () => {
    expect(validateEvent(values({ name: "A".repeat(NAME_LIMIT) }), NOW)).toEqual({});
    expect(validateEvent(values({ name: "A".repeat(NAME_LIMIT + 1) }), NOW)).toEqual({
      name: ["Use 100 characters or fewer."],
    });
  });

  it("enforces the 1000-character description boundary", () => {
    expect(
      validateEvent(values({ description: "B".repeat(DESCRIPTION_LIMIT) }), NOW),
    ).toEqual({});
    expect(
      validateEvent(values({ description: "B".repeat(DESCRIPTION_LIMIT + 1) }), NOW),
    ).toEqual({ description: ["Use 1,000 characters or fewer."] });
  });

  it("rejects blank trimmed fields and missing values", () => {
    const errors = validateEvent(
      {
        name: "   ",
        description: " ",
        date: "",
        time: "",
        location: "\t",
      },
      NOW,
    );
    expect(errors).toEqual({
      name: ["Enter an event name."],
      description: ["Add a description."],
      location: ["Add a location."],
      date: ["Choose a date."],
      time: ["Choose a time."],
    });
  });

  it("rejects past dates and times in the configured local timezone", () => {
    expect(validateEvent(values({ date: "2029-12-31" }), NOW)).toEqual({
      date: ["Choose a date and time in the future."],
    });
    expect(
      validateEvent(values({ date: "2030-01-01", time: "11:59" }), NOW),
    ).toEqual({ date: ["Choose a date and time in the future."] });
  });

  it("rejects malformed and impossible date/time values", () => {
    expect(validateEvent(values({ date: "01/02/2030" }), NOW)).toEqual({
      date: ["Use the YYYY-MM-DD format."],
    });
    expect(validateEvent(values({ date: "2030-02-31" }), NOW)).toEqual({
      date: ["Choose a valid date and time."],
    });
    expect(validateEvent(values({ time: "9am" }), NOW)).toEqual({
      time: ["Use the HH:MM format."],
    });
  });
});

describe("normalizedEventValues", () => {
  it("trims text fields without changing the date or time", () => {
    expect(
      normalizedEventValues({
        name: "  Name  ",
        description: "  Description  ",
        date: "2030-02-01",
        time: "10:00",
        location: "  Hall  ",
      }),
    ).toEqual({
      name: "Name",
      description: "Description",
      date: "2030-02-01",
      time: "10:00",
      location: "Hall",
    });
  });
});
