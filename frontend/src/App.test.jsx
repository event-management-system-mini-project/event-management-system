
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    listUpcomingEvents: vi.fn().mockResolvedValue({ events: [] }),
    createEvent: vi.fn(),
    updateEvent: vi.fn(),
    deleteEvent: vi.fn(),
    ...overrides,
  };
}

const ORGANIZER = {
  id: "organizer-1",
  username: "organizer-one",
};

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
  await user.type(
    screen.getByLabelText("Event name"),
    changes.name ?? "Spring Meetup",
  );

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

  await user.type(
    screen.getByLabelText("Location"),
    changes.location ?? "Town Hall",
  );
}

describe("organizer login", () => {
  it("signs in and loads the organizer's own event list", async () => {
    const user = userEvent.setup();

    const api = makeApi({
      login: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });

    render(<App api={api} />);

    await screen.findByRole("heading", {
      name: /sign in to manage/i,
    });

    await user.type(
      screen.getByLabelText("Username"),
      ORGANIZER.username,
    );

    await user.type(
      screen.getByLabelText("Password"),
      "synthetic-password",
    );

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      await screen.findByText(ORGANIZER.username),
    ).toBeInTheDocument();

    expect(api.login).toHaveBeenCalledWith(
      ORGANIZER.username,
      "synthetic-password",
    );

    expect(api.listOwnEvents).toHaveBeenCalled();

    expect(
      await screen.findByText("No events yet"),
    ).toBeInTheDocument();
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

    await screen.findByRole("heading", {
      name: /sign in to manage/i,
    });

    await user.type(
      screen.getByLabelText("Username"),
      "organizer-one",
    );

    await user.type(
      screen.getByLabelText("Password"),
      "wrong-password",
    );

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The username or password is incorrect.",
    );

    expect(
      screen.getByRole("button", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("signs out and removes the protected workspace", async () => {
    const user = userEvent.setup();

    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });

    render(<App api={api} />);

    await screen.findByText("No events yet");

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(
      await screen.findByRole("heading", {
        name: /sign in to manage/i,
      }),
    ).toBeInTheDocument();

    expect(screen.getByRole("status")).toHaveTextContent(
      "You have signed out.",
    );

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

    expect(
      await screen.findByRole("heading", {
        name: /sign in to manage/i,
      }),
    ).toBeInTheDocument();

    expect(screen.getByRole("status")).toHaveTextContent(
      "Your session ended.",
    );
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

    await user.click(
      screen.getByRole("button", { name: "Create event" }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Spring Meetup",
    );

    expect(
      screen.getByRole("heading", { name: "Spring Meetup" }),
    ).toBeInTheDocument();

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

    await user.click(
      screen.getByRole("button", { name: "Create event" }),
    );

    expect(
      await screen.findByText("This field is required."),
    ).toBeInTheDocument();

    expect(screen.getByLabelText("Event name")).toHaveAttribute(
      "aria-invalid",
      "true",
    );

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

    await user.click(
      screen.getByRole("button", { name: "Create event" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The event could not be saved. Try again.",
    );

    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    expect(
      screen.queryByRole("heading", { name: "Spring Meetup" }),
    ).not.toBeInTheDocument();
  });

  it("blocks the 101-character name and 1001-character description before submit", async () => {
    const user = userEvent.setup();

    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
    });

    render(<App api={api} />);

    await screen.findByText("No events yet");

    fireEvent.change(screen.getByLabelText("Event name"), {
      target: { value: "A".repeat(101) },
    });

    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "B".repeat(1001) },
    });

    await user.click(
      screen.getByRole("button", { name: "Create event" }),
    );

    expect(
      await screen.findByText("Use 100 characters or fewer."),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Use 1,000 characters or fewer."),
    ).toBeInTheDocument();

    expect(api.createEvent).not.toHaveBeenCalled();
  });
});


describe("organizer event editing", () => {
  it("prefills the edit form and updates the owned event", async () => {
    const user = userEvent.setup();
    const updated = {
      ...SAVED_EVENT,
      name: "Updated Meetup",
      location: "New Hall",
    };

    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      listOwnEvents: vi.fn().mockResolvedValue({ events: [SAVED_EVENT] }),
      updateEvent: vi.fn().mockResolvedValue({ event: updated }),
    });

    render(<App api={api} />);

    await screen.findByRole("heading", { name: "Spring Meetup" });
    await user.click(
      screen.getByRole("button", { name: "Edit Spring Meetup" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Edit event" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Event name")).toHaveValue("Spring Meetup");
    expect(screen.getByLabelText("Location")).toHaveValue("Town Hall");

    fireEvent.change(screen.getByLabelText("Event name"), {
      target: { value: "Updated Meetup" },
    });
    fireEvent.change(screen.getByLabelText("Location"), {
      target: { value: "New Hall" },
    });

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(api.updateEvent).toHaveBeenCalledWith("event-1", {
      name: "Updated Meetup",
      description: "A synthetic event.",
      date: "2099-05-20",
      time: "10:00",
      location: "New Hall",
    });

    expect(
      await screen.findByRole("heading", { name: "Updated Meetup" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Create an event" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(api.listUpcomingEvents).toHaveBeenCalledTimes(2),
    );
  });

  it("cancels editing without saving and restores the create form", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      listOwnEvents: vi.fn().mockResolvedValue({ events: [SAVED_EVENT] }),
    });

    render(<App api={api} />);

    await screen.findByRole("heading", { name: "Spring Meetup" });
    await user.click(
      screen.getByRole("button", { name: "Edit Spring Meetup" }),
    );
    await screen.findByRole("heading", { name: "Edit event" });

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(
      screen.getByRole("heading", { name: "Create an event" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Event name")).toHaveValue("");
    expect(api.updateEvent).not.toHaveBeenCalled();
  });

  it("shows server field errors in the edit form and keeps the event", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      listOwnEvents: vi.fn().mockResolvedValue({ events: [SAVED_EVENT] }),
      updateEvent: vi.fn().mockRejectedValue(
        new ApiError("Correct the invalid fields.", {
          status: 400,
          code: "invalid_input",
          fields: { name: ["This field is required."] },
        }),
      ),
    });

    render(<App api={api} />);

    await screen.findByRole("heading", { name: "Spring Meetup" });
    await user.click(
      screen.getByRole("button", { name: "Edit Spring Meetup" }),
    );
    await screen.findByRole("heading", { name: "Edit event" });

    fireEvent.change(screen.getByLabelText("Event name"), {
      target: { value: "Still a valid client value" },
    });
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await screen.findByText("This field is required."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Edit event" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Spring Meetup" }),
    ).toBeInTheDocument();
  });
});

describe("organizer event deletion", () => {
  async function openDeleteConfirmation(user) {
    await screen.findByRole("heading", { name: "Spring Meetup" });
    await user.click(
      screen.getByRole("button", { name: "Delete Spring Meetup" }),
    );
    return screen.findByRole("dialog", {
      name: /Delete “Spring Meetup”/,
    });
  }

  function authenticatedApi(overrides = {}) {
    return makeApi({
      getSession: vi.fn().mockResolvedValue({ organizer: ORGANIZER }),
      listOwnEvents: vi.fn().mockResolvedValue({ events: [SAVED_EVENT] }),
      ...overrides,
    });
  }

  it("requires explicit confirmation and can be cancelled", async () => {
    const user = userEvent.setup();
    const api = authenticatedApi();

    render(<App api={api} />);

    const dialog = await openDeleteConfirmation(user);
    expect(dialog).toHaveTextContent("all of its registrations");

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.deleteEvent).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Spring Meetup" }),
    ).toBeInTheDocument();
  });

  it("removes the event only after the delete API confirms", async () => {
    const user = userEvent.setup();
    const api = authenticatedApi({
      deleteEvent: vi.fn().mockResolvedValue({
        deleted: true,
        event_id: "event-1",
      }),
    });

    render(<App api={api} />);

    const dialog = await openDeleteConfirmation(user);
    await user.click(
      within(dialog).getByRole("button", { name: "Delete event" }),
    );

    expect(api.deleteEvent).toHaveBeenCalledWith("event-1");
    expect(await screen.findByText("No events yet")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Spring Meetup" }),
    ).not.toBeInTheDocument();
    await waitFor(() =>
      expect(api.listUpcomingEvents).toHaveBeenCalledTimes(2),
    );
  });

  it("keeps the event and shows an error when deletion fails", async () => {
    const user = userEvent.setup();
    const api = authenticatedApi({
      deleteEvent: vi.fn().mockRejectedValue(
        new ApiError("The event could not be deleted. Try again.", {
          status: 503,
          code: "database_unavailable",
        }),
      ),
    });

    render(<App api={api} />);

    const dialog = await openDeleteConfirmation(user);
    await user.click(
      within(dialog).getByRole("button", { name: "Delete event" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The event could not be deleted. Try again.",
    );
    expect(
      screen.getByRole("heading", { name: "Spring Meetup" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
