import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import EventForm from "./EventForm.jsx";

const FUTURE_DATE = "2099-05-20";

function renderForm(onSave = vi.fn().mockResolvedValue({ name: "Synthetic Event" })) {
  const onSessionExpired = vi.fn();
  render(
    <EventForm onSave={onSave} onSessionExpired={onSessionExpired} />,
  );
  return { onSave, onSessionExpired };
}

function change(label, value) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillValid(values = {}) {
  change("Event name", values.name ?? "Synthetic Workshop");
  change("Description", values.description ?? "A synthetic event.");
  change("Date", values.date ?? FUTURE_DATE);
  change("Start time (IST)", values.time ?? "10:00");
  change("Location", values.location ?? "Synthetic Hall");
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Create event" }));
}

afterEach(() => {
  vi.useRealTimers();
});

describe("organizer event form boundaries", () => {
  it("accepts a 100-character name and 1000-character description", async () => {
    const { onSave } = renderForm(
      vi.fn().mockResolvedValue({ name: "A".repeat(100) }),
    );

    // fireEvent.change models pasting a long value. Typing 1,001 characters
    // with userEvent adds no coverage and makes the regression test needlessly
    // slow in CI.
    fillValid({ name: "A".repeat(100), description: "B".repeat(1000) });
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    const submitted = onSave.mock.calls[0][0];
    expect(submitted.name).toHaveLength(100);
    expect(submitted.description).toHaveLength(1000);
    expect(screen.queryByText("Use 100 characters or fewer.")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Use 1,000 characters or fewer."),
    ).not.toBeInTheDocument();
  });

  it("rejects 101-character names and 1001-character descriptions", async () => {
    const { onSave } = renderForm();

    fillValid({ name: "A".repeat(101), description: "B".repeat(1001) });
    submit();

    expect(
      await screen.findByText("Use 100 characters or fewer."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Use 1,000 characters or fewer."),
    ).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows required-field errors and does not call the API", async () => {
    const { onSave } = renderForm();

    submit();

    expect(await screen.findByText("Enter an event name.")).toBeInTheDocument();
    expect(screen.getByText("Add a description.")).toBeInTheDocument();
    expect(screen.getByText("Add a location.")).toBeInTheDocument();
    expect(screen.getByText("Choose a date.")).toBeInTheDocument();
    expect(screen.getByText("Choose a time.")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("clears field errors after correction and submits the valid values", async () => {
    const { onSave } = renderForm(
      vi.fn().mockResolvedValue({ name: "Corrected Event" }),
    );

    submit();
    expect(await screen.findByText("Enter an event name.")).toBeInTheDocument();

    fillValid({ name: "Corrected Event" });
    expect(screen.queryByText("Enter an event name.")).not.toBeInTheDocument();
    expect(screen.queryByText("Add a description.")).not.toBeInTheDocument();
    expect(screen.queryByText("Choose a date.")).not.toBeInTheDocument();

    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      name: "Corrected Event",
      description: "A synthetic event.",
      date: FUTURE_DATE,
      time: "10:00",
      location: "Synthetic Hall",
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Saved “Corrected Event”.",
    );
  });

  it("sets the date minimum from the IST calendar date", () => {
    vi.useFakeTimers();
    // 20:00 UTC is 01:30 IST on the next calendar day.
    vi.setSystemTime(new Date("2029-12-31T20:00:00Z"));

    renderForm();

    expect(screen.getByLabelText("Date")).toHaveAttribute(
      "min",
      "2030-01-01",
    );
  });
});
