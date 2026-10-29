import { useEffect, useState } from "react";

type PosterImageProps = {
  src: string | null | undefined;
  alt: string;
  className?: string;
};

export function PosterImage({ src, alt, className = "" }: PosterImageProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [src]);

  return (
    <div className={`poster-art ${className}`.trim()}>
      {(!src || failed) && (
        <span aria-hidden="true" className="poster-art-placeholder">
          Cover unavailable
        </span>
      )}
      {src && !failed && (
        <img
          alt={alt}
          decoding="async"
          loading="lazy"
          onError={() => setFailed(true)}
          src={src}
        />
      )}
    </div>
  );
}
