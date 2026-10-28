# BL-16: Shared Navigation and Accessible UI Components

## 1. Purpose

Provide reusable, accessible UI components for attendee, organizer, and registration screens. Feature teams can reuse these components without taking ownership of one another's feature files.

## 2. Shared Components

| Component | Purpose | Main Props |
|---|---|---|
| `SharedLayout` | Common page layout, navigation, skip link, and footer | `brand`, `links`, `children`, `footer` |
| `LoadingState` | Announces loading progress | `message`, `className` |
| `ErrorState` | Displays an error and optional retry action | `message`, `onRetry`, `retryLabel` |
| `EmptyState` | Displays an empty-results message | `title`, `message`, `action` |
| `SuccessState` | Announces successful completion | `message`, `className` |
| `SharedButton` | Reusable button with loading and disabled states | `children`, `type`, `variant`, `disabled`, `loading`, `loadingLabel` |
| `FormField` | Labelled input with hints and validation errors | `label`, `name`, `type`, `value`, `onChange`, `required`, `error`, `hint` |

## 3. Accessibility

- Use semantic navigation, main content, headings, and form labels.
- Provide a skip-to-main-content link.
- Announce loading and success states with status semantics.
- Use an alert role for errors that need immediate attention.
- Associate validation messages and hints with their inputs.
- Provide visible keyboard focus indicators.
- Disable buttons while their loading state is active.

## 4. Usage Examples

### Loading

```jsx
<LoadingState message="Loading upcoming events..." />
```

### Error and retry

```jsx
<ErrorState
  message="Events could not be loaded."
  onRetry={loadEvents}
/>
```

### Empty results

```jsx
<EmptyState
  title="No upcoming events"
  message="Check back later for new events."
/>
```

### Form field

```jsx
<FormField
  label="Event name"
  name="eventName"
  value={eventName}
  onChange={(event) => setEventName(event.target.value)}
  required
  error={error}
/>
```

### Loading button

```jsx
<SharedButton type="submit" loading={saving}>
  Save event
</SharedButton>
```

### Layout

```jsx
<SharedLayout
  brand="Event Management"
  links={[{ label: "Upcoming events", href: "/" }]}
>
  <h1>Upcoming events</h1>
</SharedLayout>
```

## 5. Feature-Team Integration

- Attendee screens can reuse the shared loading, error, and empty states.
- Organizer and registration feature teams can use the shared layout examples as adapters.
- Adapters demonstrate reuse and do not imply that example URLs are implemented routes.
- Feature teams remain responsible for their own business logic, API interactions, and feature files.

## 6. Testing and Verification

Automated component tests are maintained in `frontend/src/components/shared/sharedComponents.test.jsx`.

Record the actual results for:
- Automated shared-component and attendee-flow tests.
- Keyboard navigation and visible focus.
- Form labels, validation messages, and state transitions.
- Correction after validation errors without losing entered data.
- Chrome, Firefox, and Edge checks using local fixtures.

Browser checks must be recorded only after they have actually been performed.

## 7. Acceptance Notes

The shared components and examples provide a reusable foundation. Complete adoption across organizer and attendee navigation must be verified with the relevant feature owners at sprint acceptance.
