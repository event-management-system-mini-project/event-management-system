import React from "react";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatDate(isoDate) {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!parts) return isoDate;
  const month = MONTHS[Number(parts[2]) - 1] || parts[2];
  return `${Number(parts[3])} ${month} ${parts[1]}`;
}

export default function EventList({
  events,
  loading,
  error,
  onRetry,
  onEdit,
  onDelete,
}) {
  return (
    <section className="panel" aria-labelledby="events-heading">
      <div className="panel-heading">
        <p className="eyebrow">Your schedule</p>
        <h2 id="events-heading">Your events</h2>
        <p className="panel-intro">
          Only events owned by your signed-in account are shown here.
        </p>
      </div>

      {loading ? (
        <p className="muted" role="status">
          Loading your events...
        </p>
      ) : null}

      {error && !loading ? (
        <div className="list-error" role="alert">
          <p>{error}</p>
          <button className="text-button" type="button" onClick={onRetry}>
            Try again
          </button>
        </div>
      ) : null}

      {!loading && !error && events.length === 0 ? (
        <div className="empty-state">
          <p className="empty-title">No events yet</p>
          <p className="muted">
            Create your first event with the form. Saved events appear here.
          </p>
        </div>
      ) : null}

      {!loading && !error && events.length > 0 ? (
        <ol className="event-list">
          {events.map((event) => (
            <li className="event-item" key={event.id}>
              <div className="event-when">
                <span className="event-date">{formatDate(event.date)}</span>
                <span className="event-time">{event.time.slice(0, 5)} IST</span>
              </div>
              <div className="event-body">
                <h3>{event.name}</h3>
                <p className="event-location">{event.location}</p>
                <p className="event-description">{event.description}</p>
                <div className="event-footer">
                  <p className="event-meta">
                    {event.registration_count === 1
                      ? "1 registration"
                      : `${event.registration_count} registrations`}
                  </p>
                  <div className="event-actions">
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => onEdit(event)}
                      aria-label={`Edit ${event.name}`}
                    >
                      Edit
                    </button>
                    <button
                      className="text-button danger-text"
                      type="button"
                      onClick={() => onDelete(event)}
                      aria-label={`Delete ${event.name}`}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
