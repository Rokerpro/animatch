import { Link } from "react-router-dom";
import "../styles/account.css";
import "../styles/landing.css";
import { PageTitle } from "../components/PageTitle";
import { PosterStack } from "../components/PosterStack";

export function NotFoundPage() {
  return (
    <section className="nf-page">
      <div className="nf-copy">
        <PageTitle lead="Page not found" className="nf-title" />
        <p className="nf-text">
          That link does not go anywhere. It may have moved, or the title was
          hidden.
        </p>
        <div className="nf-actions">
          <Link className="primary-action" to="/">
            Go home
          </Link>
          <Link className="secondary-action" to="/browse">
            Browse anime
          </Link>
          <Link className="secondary-action" to="/quiz">
            Take the quiz
          </Link>
        </div>
      </div>
      <PosterStack className="nf-posters" />
    </section>
  );
}
