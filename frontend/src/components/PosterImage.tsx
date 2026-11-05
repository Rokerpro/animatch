import { useState } from "react";

type PosterImageProps = {
  src: string | null | undefined;
  alt: string;
  className?: string;
};

export function PosterImage({ src, alt, className = "" }: PosterImageProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = Boolean(src && failedSrc === src);

  return (
    <div className={`poster-art ${className}`.trim()}>
      {(!src || failed) && (
        <span aria-hidden="true" className="poster-art-placeholder">
          {src ? "Image failed to load" : "Cover unavailable"}
        </span>
      )}
      {src && !failed && (
        <img
          alt={alt}
          decoding="async"
          loading="lazy"
          onError={() => setFailedSrc(src)}
          src={src}
          onLoad={(e) => {
            if ((e.target as HTMLImageElement).naturalWidth === 0) {
              setFailedSrc(src);
            }
          }}
        />
      )}
    </div>
  );
}
