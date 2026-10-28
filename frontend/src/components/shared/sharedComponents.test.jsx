
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import LoadingState from "./LoadingState.jsx";
import ErrorState from "./ErrorState.jsx";
import EmptyState from "./EmptyState.jsx";
import SuccessState from "./SuccessState.jsx";
import SharedButton from "./SharedButton.jsx";
import FormField from "./FormField.jsx";
import SharedLayout from "./SharedLayout.jsx";

describe("shared accessible components", () => {
  it("shows a loading message with status semantics", () => {
    render(<LoadingState message="Loading events..." />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading events...",
    );
  });

  it("shows an error and calls retry when clicked", () => {
    const onRetry = vi.fn();

    render(
      <ErrorState message="Could not load events" onRetry={onRetry} />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load events",
    );

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("shows the empty state title and message", () => {
    render(
      <EmptyState
        title="No events"
        message="Try again later."
      />,
    );

    expect(
      screen.getByRole("heading", { name: "No events" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Try again later.")).toBeInTheDocument();
  });

  it("announces success messages", () => {
    render(<SuccessState message="Event saved" />);

    expect(screen.getByRole("status")).toHaveTextContent("Event saved");
  });

  it("disables a button and shows its loading label while loading", () => {
    render(
      <SharedButton loading loadingLabel="Saving...">
        Save event
      </SharedButton>,
    );

    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  });

  it("associates a visible label and validation error with an input", () => {
    render(
      <FormField
        label="Event name"
        name="eventName"
        value=""
        onChange={() => {}}
        required
        error="Event name is required"
      />,
    );

    const input = screen.getByRole("textbox", { name: /Event name/ });

    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Event name is required");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Event name is required",
    );
  });

  it("renders accessible navigation and a main-content skip link", () => {
    render(
      <SharedLayout
        brand="Campus Events"
        links={[
          { label: "Upcoming events", href: "/events" },
          { label: "Sign in", href: "/login" },
        ]}
      >
        <h1>Welcome</h1>
      </SharedLayout>,
    );

    expect(
      screen.getByRole("navigation", { name: "Main navigation" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Upcoming events" }),
    ).toHaveAttribute("href", "/events");

    expect(
      screen.getByRole("link", { name: "Skip to main content" }),
    ).toHaveAttribute("href", "#main-content");

    expect(screen.getByRole("main")).toHaveTextContent("Welcome");
  });
});
