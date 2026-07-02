import './QueryError.css';

interface QueryErrorProps {
  /** What failed to load, e.g. "journal entries" */
  what: string;
  /** Retry callback — usually the query's refetch function */
  onRetry?: () => void;
}

/** Inline error notice for failed data fetches.
 *
 *  Shown in place of a list when its query errors, so a backend
 *  failure never masquerades as an empty list ("No entries yet")
 *  and makes the user think their data is gone. */
export default function QueryError({ what, onRetry }: QueryErrorProps) {
  return (
    <div className="query-error" role="alert">
      <p className="query-error__message">
        Couldn't load {what}.
      </p>
      <p className="query-error__hint">
        Your data is safe — the app just couldn't reach its backend.
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Try Again
        </button>
      )}
    </div>
  );
}
