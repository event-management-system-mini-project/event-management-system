import { describe, expect, it } from "vitest";

import {
  DESCRIPTION_LIMIT,
  NAME_LIMIT,
  earliestSelectableDate,
  normalizedEventValues,
  validateEvent,
} from "./validation.js";

// 2030-01-01 12:00 IST. Fixed instants keep these checks independent of the
// browser's local timezone.
const NOW = new Date("2030-01-01T06:30:00.000Z");

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

  it("rejects past dates and times using the IST event contract", () => {
    expect(validateEvent(values({ date: "2029-12-31" }), NOW)).toEqual({
      date: ["Choose a date and time in the future."],
    });
    expect(
      validateEvent(values({ date: "2030-01-01", time: "11:59" }), NOW),
    ).toEqual({ date: ["Choose a date and time in the future."] });
    expect(
      validateEvent(values({ date: "2030-01-01", time: "12:01" }), NOW),
    ).toEqual({});
  });

  it("handles same-day and midnight boundaries in IST", () => {
    const startOfDay = new Date("2029-12-31T18:30:00.000Z"); // 2030-01-01 00:00 IST
    expect(
      validateEvent(values({ date: "2030-01-01", time: "00:00" }), startOfDay),
    ).toEqual({ date: ["Choose a date and time in the future."] });
    expect(
      validateEvent(values({ date: "2030-01-01", time: "00:01" }), startOfDay),
    ).toEqual({});
    expect(
      validateEvent(values({ date: "2029-12-31", time: "23:59" }), startOfDay),
    ).toEqual({ date: ["Choose a date and time in the future."] });

    const endOfDay = new Date("2030-01-01T18:29:00.000Z"); // 2030-01-01 23:59 IST
    expect(
      validateEvent(values({ date: "2030-01-01", time: "23:59" }), endOfDay),
    ).toEqual({ date: ["Choose a date and time in the future."] });
    expect(
      validateEvent(values({ date: "2030-01-02", time: "00:00" }), endOfDay),
    ).toEqual({});
  });

  it("uses the same result for one instant written in IST, UTC and US Pacific offsets", () => {
    const sameInstant = [
      new Date("2030-01-01T12:00:00+05:30"),
      new Date("2030-01-01T06:30:00Z"),
      new Date("2029-12-31T22:30:00-08:00"),
    ];
    for (const now of sameInstant) {
      expect(
        validateEvent(values({ date: "2030-01-01", time: "12:01" }), now),
      ).toEqual({});
      expect(
        validateEvent(values({ date: "2030-01-01", time: "11:59" }), now),
      ).toEqual({ date: ["Choose a date and time in the future."] });
    }
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

describe("earliestSelectableDate", () => {
  it("uses the IST calendar date rather than the browser's local date", () => {
    // 20:00 UTC is already 01:30 IST on the next day.
    expect(earliestSelectableDate(new Date("2029-12-31T20:00:00Z"))).toBe(
      "2030-01-01",
    );
    expect(earliestSelectableDate(new Date("2029-12-31T18:29:00Z"))).toBe(
      "2029-12-31",
    );
    expect(earliestSelectableDate(new Date("2030-01-01T18:29:00Z"))).toBe(
      "2030-01-01",
    );
    expect(earliestSelectableDate(new Date("2030-01-01T18:30:00Z"))).toBe(
      "2030-01-02",
    );
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
