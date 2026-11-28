import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useSeasons } from "../api/hooks";
import { episodesText, extraMeta } from "./formatMeta";
import { PosterImage } from "./PosterImage";

export function SeasonsSection({
  animeId,
  mature,
}: {
  animeId: number;
  mature: boolean;
}) {
  const seasons = useSeasons(animeId, mature);
  const trackRef = useRef<HTMLOListElement>(null);
  const [scroll, setScroll] = useState({ back: false, forward: false });
  const main = seasons.data?.main ?? [];
  const extras = seasons.data?.extras ?? [];

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const update = () =>
      setScroll({
        back: track.scrollLeft > 4,
        forward: track.scrollLeft + track.clientWidth < track.scrollWidth - 4,
      });
    update();
    track
      .querySelector<HTMLElement>("[aria-current='page']")
      ?.scrollIntoView?.({
        block: "nearest",
        inline: "nearest",
      });
    track.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      track.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [main.length]);

  // Standalone shows (and failed requests) leave the section out entirely.
  if (!main.length && !extras.length) return null;

  function page(direction: 1 | -1) {
    const track = trackRef.current;
    track?.scrollBy?.({
      left: direction * track.clientWidth * 0.8,
      behavior: "smooth",
    });
  }

  return (
    <section aria-labelledby="seasons-title" className="title-section seasons">
      <h2 className="title-section-heading" id="seasons-title">
        Seasons and related
      </h2>
      {main.length > 1 && (
        <>
          <p className="title-section-sub">
            {main.length} entries in the main story, in release order
          </p>
          <div className="seasons-strip">
            <ol className="seasons-track" ref={trackRef}>
              {main.map((item) => {
                const body = (
                  <>
                    <PosterImage
                      alt=""
                      color={item.coverColor}
                      src={item.coverImage}
                    />
                    <span className="season-copy">
                      <span className="season-year">{item.year ?? "TBA"}</span>
                      <span className="season-title">{item.title}</span>
                      <span className="season-foot">
                        {item.isCurrent
                          ? "You're here"
                          : episodesText(item.episodes)}
                      </span>
                    </span>
                  </>
                );
                return (
                  <li key={item.id}>
                    {item.isCurrent ? (
                      <div
                        aria-current="page"
                        className="season-card is-current"
                      >
                        {body}
                      </div>
                    ) : (
                      <Link className="season-card" to={`/anime/${item.id}`}>
                        {body}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ol>
            {scroll.back && (
              <button
                aria-label="Earlier seasons"
                className="seasons-nav is-back"
                onClick={() => page(-1)}
                type="button"
              >
                <ChevronLeft aria-hidden="true" size={18} strokeWidth={1.5} />
              </button>
            )}
            {scroll.forward && (
              <button
                aria-label="Later seasons"
                className="seasons-nav"
                onClick={() => page(1)}
                type="button"
              >
                <ChevronRight aria-hidden="true" size={18} strokeWidth={1.5} />
              </button>
            )}
          </div>
        </>
      )}
      {extras.length > 0 && (
        <>
          <h3 className="extras-heading">
            Movies, OVAs and side stories <span>Optional</span>
          </h3>
          <ul className="extras-grid">
            {extras.map((extra) => (
              <li key={extra.id}>
                <Link className="extra-card" to={`/anime/${extra.id}`}>
                  <PosterImage
                    alt=""
                    color={extra.coverColor}
                    src={extra.coverImage}
                  />
                  <span className="extra-copy">
                    <span className="extra-title">{extra.title}</span>
                    <span className="extra-meta">{extraMeta(extra)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
