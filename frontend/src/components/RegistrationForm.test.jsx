import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import { ApiError } from "../api.js";

const event = { id: "event-one", name: "Community meetup", description: "Meet locally",
  date: "2099-01-01", time: "10:00:00", location: "Hall", registration_count: 0 };

function apiFor(organizer = null) {
  return {
    getSession: vi.fn().mockResolvedValue({ organizer }),
    listOwnEvents: vi.fn().mockResolvedValue({ events: [] }),
    listUpcomingEvents: vi.fn().mockResolvedValue({ events: [event] }),
    registerForEvent: vi.fn().mockResolvedValue({ id: "new-registration" }),
  };
}

async function openAndFill() {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Register for Community meetup" }));
  const form = screen.getByRole("region", { name: "Register for Community meetup" });
  fireEvent.change(within(form).getByLabelText("Your Name"), { target: { value: "Synthetic Attendee" } });
  fireEvent.change(within(form).getByLabelText("Your Email"), { target: { value: "attendee@example.com" } });
  return { user, form };
}

describe("attendee registration from the event list", () => {
  for (const organizer of [null, { id: "owner-one", username: "organizer" }]) {
    it(`registers and refreshes the count with ${organizer ? "an organizer session" : "no login"}`, async () => {
      const api = apiFor(organizer);
      api.listUpcomingEvents.mockResolvedValueOnce({ events: [event] })
        .mockResolvedValue({ events: [{ ...event, registration_count: 1 }] });
      render(<App api={api} />);
      const { user, form } = await openAndFill();
      await user.click(within(form).getByRole("button", { name: "Register for Event" }));
      expect(api.registerForEvent).toHaveBeenCalledWith(event.id,
        { name: "Synthetic Attendee", email: "attendee@example.com" });
      expect(await screen.findByText("1 registration")).toBeInTheDocument();
      expect(screen.getByText("Successfully registered!")).toBeInTheDocument();
    });
  }

  it("shows duplicate errors, retains entered details and does not increment the count", async () => {
    const api = apiFor();
    api.registerForEvent.mockRejectedValue(new ApiError("Already registered.", {
      status: 400, fields: { email: ["This email is already registered for this event."] },
    }));
    render(<App api={api} />);
    const { user, form } = await openAndFill();
    await user.click(within(form).getByRole("button", { name: "Register for Event" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already registered");
    expect(within(form).getByLabelText("Your Email")).toHaveValue("attendee@example.com");
    expect(api.listUpcomingEvents).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Successfully registered!")).not.toBeInTheDocument();
  });

  it("prevents repeat submission while a registration is pending", async () => {
    const api = apiFor();
    let finish;
    api.registerForEvent.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    render(<App api={api} />);
    const { user, form } = await openAndFill();
    await user.click(within(form).getByRole("button", { name: "Register for Event" }));
    expect(within(form).getByRole("button", { name: "Registering..." })).toBeDisabled();
    expect(within(form).getByLabelText("Your Email")).toBeDisabled();
    finish({ id: "registered" });
    await waitFor(() => expect(screen.getByText("Successfully registered!")).toBeInTheDocument());
    expect(api.registerForEvent).toHaveBeenCalledTimes(1);
  });
});
