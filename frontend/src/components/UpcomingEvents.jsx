
import React, { useCallback, useEffect, useState } from "react";

import LoadingState from "./shared/LoadingState.jsx";
import ErrorState from "./shared/ErrorState.jsx";
import EmptyState from "./shared/EmptyState.jsx";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function formatDate(isoDate) {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);

  if (!parts) return isoDate;

  const month = MONTHS[Number(parts[2]) - 1] || parts[2];

  return `${Number(parts[3])} ${month} ${parts[1]}`;
}

function sortEvents(events) {
  return [...events].sort((left, right) =>
    `${left.date}T${left.time}`.localeCompare(
      `${right.date}T${right.time}`,
    ),
  );
}

export default function UpcomingEvents({ api, refreshKey = 0 }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await api.listUpcomingEvents();
      setEvents(sortEvents(data.events || []));
    } catch (err) {
      setError(
        err.message || "Upcoming events could not be loaded. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [api, refreshKey]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  return (
    <section className="panel" aria-labelledby="upcoming-events-heading">
      <div className="panel-heading">
        <p className="eyebrow">Open to everyone</p>

        <h2 id="upcoming-events-heading">Upcoming events</h2>

        <p className="panel-intro">
          Explore events scheduled for the future.
        </p>
      </div>

      {loading ? (
        <LoadingState
          message="Loading upcoming events..."
          className="muted"
        />
      ) : null}

      {error && !loading ? (
        <ErrorState
          message={error}
          onRetry={loadEvents}
          retryLabel="Try again"
        />
      ) : null}

      {!loading && !error && events.length === 0 ? (
        <EmptyState
          title="No upcoming events"
          message="Check back later for new events."
        />
      ) : null}

      {!loading && !error && events.length > 0 ? (
        <ol className="event-list">
          {events.map((event) => (
            <li className="event-item" key={event.id}>
              <div className="event-when">
                <span className="event-date">
                  {formatDate(event.date)}
                </span>

                <span className="event-time">
                  {event.time.slice(0, 5)} IST
                </span>
              </div>

              <div className="event-body">
                <h3>{event.name}</h3>

                <p className="event-location">{event.location}</p>

                <p className="event-description">
                  {event.description}
                </p>

                {Number.isInteger(event.registration_count) ? (
                  <p className="event-meta">
                    {event.registration_count === 1
                      ? "1 registration"
                      : `${event.registration_count} registrations`}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
