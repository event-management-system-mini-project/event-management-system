import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App.jsx";
import { ApiError } from "./api.js";

function makeApi(overrides = {}) {
  return {
    getSession: vi.fn().mockResolvedValue({ organizer: null }),
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue({ logged_out: true }),
    listOwnEvents: vi.fn().mockResolvedValue({ events: [] }),
    createEvent: vi.fn(),
    ...overrides,
  };
}

const ORGANIZER = { id: "organizer-1", username: "organizer-one" };

const SAVED_EVENT = {
  id: "event-1",
  name: "Spring Meetup",
  description: "A synthetic event.",
  date: "2099-05-20",
  time: "10:00:00",
  location: "Town Hall",
  registration_count: 0,
};

async function fillEventForm(user, changes = {}) {
  await user.type(screen.getByLabelText("Event name"), changes.name ?? "Spring Meetup");
  await user.type(
    screen.getByLabelText("Description"),
    changes.description ?? "A synthetic event.",
  );
  fireEvent.change(screen.getByLabelText("Date"), {
    target: { value: changes.date ?? "2099-05-20" },
  });
  fireEvent.change(screen.getByLabelText("Start time (IST)"), {
    target: { value: changes.time ?? "10:00" },
  });
  await user.type(screen.getByLabelText("Location"), changes.location ?? "Town Hall");
}

describe("organizer login", () => {
  it("signs in and loads the organizer's own event list", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      login: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });
    render(<App api={api} />);

    await screen.findByRole("heading", { name: /sign in to manage/i });
    await user.type(screen.getByLabelText("Username"), ORGANIZER.username);
    await user.type(screen.getByLabelText("Password"), "synthetic-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText(ORGANIZER.username)).toBeInTheDocument();
    expect(api.login).toHaveBeenCalledWith(ORGANIZER.username, "synthetic-password");
    expect(api.listOwnEvents).toHaveBeenCalled();
    expect(await screen.findByText("No events yet")).toBeInTheDocument();
  });

  it("shows the invalid-credential message without leaving the page", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      login: vi.fn().mockRejectedValue(
        new ApiError("The username or password is incorrect.", {
          status: 401,
          code: "invalid_credentials",
        }),
      ),
    });
    render(<App api={api} />);

    await screen.findByRole("heading", { name: /sign in to manage/i });
    await user.type(screen.getByLabelText("Username"), "organizer-one");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The username or password is incorrect.",
    );
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("signs out and removes the protected workspace", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });
    render(<App api={api} />);

    await screen.findByText("No events yet");
    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: /sign in to manage/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You have signed out.");
    expect(api.logout).toHaveBeenCalled();
  });

  it("returns to login when a protected request reports an expired session", async () => {
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      listOwnEvents: vi.fn().mockRejectedValue(
        new ApiError("Organizer authentication is required.", {
          status: 401,
          code: "authentication_required",
        }),
      ),
    });
    render(<App api={api} />);

    expect(await screen.findByRole("heading", { name: /sign in to manage/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Your session ended.");
  });
});

describe("organizer event creation", () => {
  it("shows the new event only after the API confirms the save", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      createEvent: vi.fn().mockResolvedValue({ event: SAVED_EVENT }),
    });
    render(<App api={api} />);

    await screen.findByText("No events yet");
    await fillEventForm(user);
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Spring Meetup");
    expect(screen.getByRole("heading", { name: "Spring Meetup" })).toBeInTheDocument();
    expect(api.createEvent).toHaveBeenCalledWith({
      name: "Spring Meetup",
      description: "A synthetic event.",
      date: "2099-05-20",
      time: "10:00",
      location: "Town Hall",
    });
    expect(screen.getByLabelText("Event name")).toHaveValue("");
  });

  it("maps server field errors onto the form", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      createEvent: vi.fn().mockRejectedValue(
        new ApiError("Correct the invalid fields.", {
          status: 400,
          code: "invalid_input",
          fields: { name: ["This field is required."] },
        }),
      ),
    });
    render(<App api={api} />);

    await screen.findByText("No events yet");
    await fillEventForm(user);
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(await screen.findByText("This field is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Event name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows a clear failure and no success state on a database error", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      createEvent: vi.fn().mockRejectedValue(
        new ApiError("The event could not be saved. Try again.", {
          status: 503,
          code: "database_unavailable",
        }),
      ),
    });
    render(<App api={api} />);

    await screen.findByText("No events yet");
    await fillEventForm(user);
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The event could not be saved. Try again.",
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Spring Meetup" })).not.toBeInTheDocument();
  });

  it("blocks the 101-character name and 1001-character description before submit", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });
    render(<App api={api} />);

    await screen.findByText("No events yet");
    await fillEventForm(user, {
      name: "A".repeat(101),
      description: "B".repeat(1001),
    });
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(await screen.findByText("Use 100 characters or fewer.")).toBeInTheDocument();
    expect(screen.getByText("Use 1,000 characters or fewer.")).toBeInTheDocument();
    expect(api.createEvent).not.toHaveBeenCalled();
  });
});
