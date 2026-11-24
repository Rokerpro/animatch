import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PosterImage } from "./PosterImage";

/**
 * Three staggered covers from the most popular catalog titles. Purely
 * decorative: hidden from assistive tech and always safe for work.
 */
export function PosterStack({ className = "" }: { className?: string }) {
  const popular = useQuery({
    queryKey: ["poster-stack"],
    queryFn: () =>
      api.anime({
        sort: "popularity",
        page: 1,
        pageSize: 3,
        includeMature: false,
      }),
    retry: false,
    staleTime: 10 * 60 * 1000,
  });
  const items = popular.data?.items ?? [];
  return (
    <div aria-hidden="true" className={`poster-stack ${className}`.trim()}>
      {[0, 1, 2].map((index) => {
        const anime = items[index];
        return (
          <div className="poster-stack-item" key={index}>
            <PosterImage
              alt=""
              color={anime?.coverColor}
              src={anime?.coverImage}
            />
          </div>
        );
      })}
    </div>
  );
}
