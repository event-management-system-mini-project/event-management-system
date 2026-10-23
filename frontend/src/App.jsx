
import React, { useCallback, useEffect, useState } from "react";

import * as defaultApi from "./api.js";
import ConfirmDelete from "./components/ConfirmDelete.jsx";
import EventForm from "./components/EventForm.jsx";
import EventList from "./components/EventList.jsx";
import LoginForm from "./components/LoginForm.jsx";
import UpcomingEvents from "./components/UpcomingEvents.jsx";

function sortEvents(events) {
  return [...events].sort((left, right) =>
    `${left.date}T${left.time}`.localeCompare(
      `${right.date}T${right.time}`,
    ),
  );
}

function OrganizerDashboard({
  api,
  organizer,
  onSignedOut,
  onSessionExpired,
  onEventsChanged,
}) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [logoutError, setLogoutError] = useState("");
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setLoadError("");

    try {
      const data = await api.listOwnEvents();
      setEvents(sortEvents(data.events || []));
    } catch (error) {
      if (error.status === 401) {
        onSessionExpired();
        return;
      }

      setLoadError(error.message || "Your events could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [api, onSessionExpired]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  async function handleSave(values) {
    if (editingEvent) {
      const data = await api.updateEvent(editingEvent.id, values);
      setEvents((current) =>
        sortEvents(
          current.map((item) => (item.id === data.event.id ? data.event : item)),
        ),
      );
      setEditingEvent(null);
      onEventsChanged();
      return data.event;
    }

    const data = await api.createEvent(values);
    setEvents((current) => sortEvents([...current, data.event]));
    onEventsChanged();
    return data.event;
  }

  function requestDelete(event) {
    setDeleteError("");
    setPendingDelete(event);
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    setDeleteError("");
    setDeleteBusy(true);
    try {
      await api.deleteEvent(pendingDelete.id);
      setEvents((current) =>
        current.filter((item) => item.id !== pendingDelete.id),
      );
      if (editingEvent?.id === pendingDelete.id) setEditingEvent(null);
      setPendingDelete(null);
      onEventsChanged();
    } catch (error) {
      if (error.status === 401) {
        onSessionExpired();
        return;
      }
      setDeleteError(
        error.message || "The event could not be deleted. Nothing was removed.",
      );
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleLogout() {
    setLogoutError("");
    setLogoutBusy(true);

    try {
      await api.logout();
      onSignedOut();
    } catch (error) {
      if (error.status === 401) {
        onSessionExpired();
      } else {
        setLogoutError(error.message || "Sign out failed. Try again.");
      }
    } finally {
      setLogoutBusy(false);
    }
  }

  return (
    <>
      <section
        className="dashboard-intro"
        aria-labelledby="dashboard-heading"
      >
        <p className="eyebrow">Organizer workspace</p>
        <h1 id="dashboard-heading">Plan the next gathering.</h1>
        <p className="lede">
          Signed in as <strong>{organizer.username}</strong>. Events are tied
          to your verified account.
        </p>

        {logoutError ? (
          <p className="form-alert" role="alert">
            {logoutError}
          </p>
        ) : null}
      </section>

      <div className="dashboard-grid">
        <EventForm
          mode={editingEvent ? "edit" : "create"}
          event={editingEvent}
          onSave={handleSave}
          onCancel={() => setEditingEvent(null)}
          onSessionExpired={onSessionExpired}
        />

        <EventList
          events={events}
          loading={loading}
          error={loadError}
          onRetry={loadEvents}
          onEdit={setEditingEvent}
          onDelete={requestDelete}
        />
      </div>

      {pendingDelete ? (
        <ConfirmDelete
          event={pendingDelete}
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => {
            if (!deleteBusy) setPendingDelete(null);
          }}
          onConfirm={handleDelete}
        />
      ) : null}

      <section className="account-panel" aria-labelledby="account-heading">
        <div>
          <h2 id="account-heading">Account</h2>
          <p className="muted">
            Signing out ends this server session and removes access to
            protected event actions.
          </p>
        </div>

        <button
          className="button secondary"
          type="button"
          onClick={handleLogout}
          disabled={logoutBusy}
        >
          {logoutBusy ? "Signing out..." : "Sign out"}
        </button>
      </section>
    </>
  );
}

export default function App({ api = defaultApi }) {
  const [session, setSession] = useState(undefined);
  const [bootError, setBootError] = useState("");
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [eventsVersion, setEventsVersion] = useState(0);

  useEffect(() => {
    let active = true;

    setBootError("");
    setSession(undefined);

    api
      .getSession()
      .then((data) => {
        if (active) {
          setSession(data.organizer || null);
        }
      })
      .catch((error) => {
        if (!active) return;

        setBootError(
          error.message || "The organizer session could not be loaded.",
        );
        setSession(null);
      });

    return () => {
      active = false;
    };
  }, [api, attempt]);

  const handleLogin = useCallback(
    async (username, password) => {
      setNotice("");
      const data = await api.login(username, password);
      setSession(data.organizer);
    },
    [api],
  );

  const handleSessionExpired = useCallback(() => {
    setSession(null);
    setNotice("Your session ended. Sign in again to manage events.");
  }, []);

  const handleSignedOut = useCallback(() => {
    setSession(null);
    setNotice("You have signed out.");
  }, []);

  const handleEventsChanged = useCallback(() => {
    setEventsVersion((current) => current + 1);
  }, []);

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>Event Management</span>
        </div>
        <span className="environment">Organizer workspace</span>
      </header>

      <main className="page">
        {session === undefined && !bootError ? (
          <p className="boot-status" role="status">
            Checking your session...
          </p>
        ) : null}

        {bootError ? (
          <section
            className="auth-panel"
            aria-labelledby="boot-error-heading"
          >
            <p className="eyebrow">Connection problem</p>
            <h1 id="boot-error-heading">
              The organizer service is unavailable
            </h1>
            <p className="lede" role="alert">
              {bootError}
            </p>
            <button
              className="button"
              type="button"
              onClick={() => setAttempt((current) => current + 1)}
            >
              Try again
            </button>
          </section>
        ) : null}

        {/* Public upcoming events are available without signing in. */}
        {!bootError ? (
          <UpcomingEvents api={api} refreshKey={eventsVersion} />
        ) : null}

        {session === null && !bootError ? (
          <div className="auth-wrap">
            {notice ? (
              <p className="session-notice" role="status">
                {notice}
              </p>
            ) : null}
            <LoginForm onLogin={handleLogin} />
          </div>
        ) : null}

        {session ? (
          <OrganizerDashboard
            api={api}
            organizer={session}
            onSignedOut={handleSignedOut}
            onSessionExpired={handleSessionExpired}
            onEventsChanged={handleEventsChanged}
          />
        ) : null}
      </main>

      <footer className="site-footer">
        <p>Event Management System · Local development build</p>
      </footer>
    </div>
  );
}
