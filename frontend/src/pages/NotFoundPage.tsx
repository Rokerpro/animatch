import { Link } from "react-router-dom";
import "../styles/account.css";
import { PageTitle } from "../components/PageTitle";
import { PosterStack } from "../components/PosterStack";

export function NotFoundPage() {
  return (
    <section className="not-found-page">
      <div className="not-found-copy">
        <PageTitle lead="Page" accent="Not Found" className="not-found-title" />
        <p className="not-found-text">
          This page doesn't exist or has moved. Check the address, or pick up
          from one of these.
        </p>
        <div className="button-row not-found-actions">
          <Link className="primary-action" to="/">
            Back to home
          </Link>
          <Link className="secondary-action" to="/browse">
            Browse anime
          </Link>
          <Link className="secondary-action" to="/quiz">
            Take the quiz
          </Link>
        </div>
      </div>
      <PosterStack className="not-found-posters" />
    </section>
  );
}
