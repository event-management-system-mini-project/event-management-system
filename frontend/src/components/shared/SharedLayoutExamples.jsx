
import React from "react";
import SharedLayout from "./SharedLayout.jsx";

/**
 * Example layouts for feature teams.
 *
 * These adapters demonstrate how organizer and registration
 * screens can reuse SharedLayout without owning or modifying
 * each other's feature components.
 */

export function OrganizerLayoutExample({ children }) {
  return (
    <SharedLayout
      brand="Event Management"
      links={[
        { label: "Upcoming events", href: "/" },
        { label: "Organizer dashboard", href: "/organizer" },
      ]}
      footer="Organizer workspace"
    >
      {children}
    </SharedLayout>
  );
}

export function RegistrationLayoutExample({ children }) {
  return (
    <SharedLayout
      brand="Event Management"
      links={[
        { label: "Upcoming events", href: "/" },
        { label: "My registrations", href: "/registrations" },
      ]}
      footer="Attendee registration"
    >
      {children}
    </SharedLayout>
  );
}
