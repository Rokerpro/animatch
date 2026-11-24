import "../styles/landing.css";
import { useRef, useState, type CSSProperties, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAnimeDetail } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PageTitle } from "../components/PageTitle";
import { PosterImage } from "../components/PosterImage";
import { TitleAutocomplete } from "../components/TitleAutocomplete";
import { readSavedQuiz } from "../quizStorage";
import { readSavedStart } from "../startStorage";

interface ShowcaseTitle {
  id: number;
  title: string;
  native: string;
  meta?: string;
  /** Used until the catalog has AniList's own cover color. */
  tint: string;
}

interface CuratedPair {
  loved: ShowcaseTitle;
  next: ShowcaseTitle;
  reason: string;
}

const HERO_PAIR: CuratedPair = {
  loved: { id: 457, title: "Mushi-shi", native: "蟲師", tint: "#c48a57" },
  next: {
    id: 4081,
    title: "Natsume's Book of Friends",
    native: "夏目友人帳",
    meta: "2008, 13 episodes",
    tint: "#6fd84a",
  },
  reason:
    "Quiet, episodic stories about people and spirits. Gentle, a little sad, and always kind.",
};

const MORE_PAIRS: CuratedPair[] = [
  {
    loved: { id: 1, title: "Cowboy Bebop", native: "", tint: "#f0674a" },
    next: {
      id: 101281,
      title: "Carole & Tuesday",
      native: "",
      tint: "#e9a04f",
    },
    reason:
      "Same director, music at the heart of every episode, and outsiders finding their own way.",
  },
  {
    loved: { id: 154587, title: "Frieren", native: "", tint: "#8fd47a" },
    next: {
      id: 21827,
      title: "Violet Evergarden",
      native: "",
      tint: "#3f7fe6",
    },
    reason:
      "Both follow someone learning, years too late, what the people around them meant.",
  },
  {
    loved: { id: 20464, title: "Haikyu!!", native: "", tint: "#f0a04b" },
    next: {
      id: 101903,
      title: "Run with the Wind",
      native: "",
      tint: "#4a6fe0",
    },
    reason:
      "A team of misfits, one shared goal, and the work it takes shown in full.",
  },
  {
    loved: { id: 97986, title: "Made in Abyss", native: "", tint: "#e6cfa3" },
    next: {
      id: 98707,
      title: "Land of the Lustrous",
      native: "",
      tint: "#e9606f",
    },
    reason: "Beautiful worlds that turn out far crueler than they first look.",
  },
];

function useCover(title: ShowcaseTitle) {
  const { mature } = useAuth();
  const detail = useAnimeDetail(title.id, mature);
  return {
    src: detail.data?.coverImage ?? null,
    color: detail.data?.coverColor ?? title.tint,
  };
}

function ShowcaseCover({
  title,
  className = "",
}: {
  title: ShowcaseTitle;
  className?: string;
}) {
  const cover = useCover(title);
  const style = { "--cover-tint": cover.color } as CSSProperties;
  return (
    <Link
      aria-label={title.title}
      className={`landing-cover ${className}`.trim()}
      style={style}
      to={`/anime/${title.id}`}
    >
      <PosterImage alt="" color={cover.color} src={cover.src} />
    </Link>
  );
}

function PairCovers({ pair }: { pair: CuratedPair }) {
  const loved = useCover(pair.loved);
  const next = useCover(pair.next);
  return (
    <div aria-hidden="true" className="pair-covers">
      <div
        className="pair-cover pair-cover-back"
        style={{ "--cover-tint": loved.color } as CSSProperties}
      >
        <PosterImage alt="" color={loved.color} src={loved.src} />
      </div>
      <div
        className="pair-cover pair-cover-front"
        style={{ "--cover-tint": next.color } as CSSProperties}
      >
        <PosterImage alt="" color={next.color} src={next.src} />
      </div>
    </div>
  );
}

function HeroSearch() {
  const { mature } = useAuth();
  const navigate = useNavigate();
  const formRef = useRef<HTMLFormElement>(null);
  const [message, setMessage] = useState("");
  const [searching, setSearching] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = formRef.current?.querySelector<HTMLInputElement>(
      "input[role='combobox']"
    );
    const query = input?.value.trim() ?? "";
    if (!query) {
      setMessage("Type the name of an anime first.");
      input?.focus();
      return;
    }
    setMessage("");
    setSearching(true);
    try {
      const response = await api.anime({
        q: query,
        page: 1,
        pageSize: 1,
        includeMature: mature,
      });
      const first = response.items[0];
      if (first) navigate(`/similar/${first.id}`);
      else setMessage(`No anime found for “${query}”.`);
    } catch {
      setMessage("Could not search right now. Try again.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <form
      className="landing-search"
      onSubmit={(event) => void submit(event)}
      ref={formRef}
      role="search"
    >
      <div className="landing-search-field">
        <TitleAutocomplete
          includeMature={mature}
          inputLabel="Anime you love"
          onSelect={(anime) => navigate(`/similar/${anime.id}`)}
          placeholder="Mushi-shi"
          selected={[]}
        />
        <button className="primary-action" disabled={searching} type="submit">
          {searching ? "Searching…" : "Find matches"}
        </button>
      </div>
      {message && (
        <p className="landing-search-message" role="alert">
          {message}
        </p>
      )}
    </form>
  );
}

export function LandingPage() {
  const location = useLocation();
  const saved = readSavedQuiz() || readSavedStart();
  if (saved && !location.state?.showHome)
    return <Navigate to="/results" replace />;

  const { loved, next, reason } = HERO_PAIR;
  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <PageTitle
            accent="you love."
            className="landing-title"
            lead="Name one anime"
          />
          <p className="landing-lede">
            AniMatch finds shows with the same feel and tells you why each one
            fits.
          </p>
          <HeroSearch />
          <p className="landing-alt muted">
            Not sure what to name?{" "}
            <Link className="text-link" to="/quiz">
              Take the quiz instead.
            </Link>
          </p>
        </div>

        <figure className="landing-showcase">
          <div className="showcase-pair">
            <div className="showcase-item showcase-loved">
              <p className="showcase-label muted">You loved</p>
              <p className="showcase-title">{loved.title}</p>
              <p className="showcase-meta muted" lang="ja">
                {loved.native}
              </p>
              <ShowcaseCover title={loved} />
            </div>
            <div className="showcase-item showcase-next">
              <p className="showcase-label muted">Try next</p>
              <p className="showcase-title">{next.title}</p>
              <p className="showcase-meta muted">
                <span lang="ja">{next.native}</span>
                {next.meta && <span>{next.meta}</span>}
              </p>
              <ShowcaseCover title={next} />
            </div>
          </div>
          <figcaption className="showcase-reason">{reason}</figcaption>
        </figure>
      </section>

      <section aria-labelledby="pairs-title" className="landing-pairs">
        <h2 className="section-title" id="pairs-title">
          More Pairs <span className="accent">to Try</span>
        </h2>
        <ul className="pair-grid">
          {MORE_PAIRS.map((pair) => (
            <li className="pair-card" key={pair.loved.id}>
              <PairCovers pair={pair} />
              <h3 className="pair-title">
                <Link to={`/similar/${pair.loved.id}`}>
                  {pair.loved.title} to {pair.next.title}
                </Link>
              </h3>
              <p className="pair-reason muted">{pair.reason}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Other ways to start" className="landing-strip">
        <div className="strip-item">
          <div>
            <h2 className="strip-title">Rather answer questions?</h2>
            <p className="muted">
              A short quiz about what you like to watch works too.
            </p>
          </div>
          <Link className="secondary-action" to="/quiz">
            Take the quiz
          </Link>
        </div>
        <div className="strip-item">
          <div>
            <h2 className="strip-title">Already on MyAnimeList?</h2>
            <p className="muted">
              Import your list to bring your watch history into AniMatch.
            </p>
          </div>
          <Link className="secondary-action" to="/import">
            Import from MyAnimeList
          </Link>
        </div>
      </section>
    </div>
  );
}
