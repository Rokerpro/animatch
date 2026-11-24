import { useState, type CSSProperties } from "react";
import { ImageIcon } from "lucide-react";

type PosterImageProps = {
  src: string | null | undefined;
  alt: string;
  color?: string | null;
  className?: string;
};

export function PosterImage({
  src,
  alt,
  color,
  className = "",
}: PosterImageProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = Boolean(src && failedSrc === src);
  const showImage = Boolean(src && !failed);
  // AniList's cover color tints the frame while the image loads.
  const style: CSSProperties | undefined = color
    ? { backgroundColor: `color-mix(in srgb, ${color} 22%, var(--surface))` }
    : undefined;

  return (
    <div
      className={`poster-art${showImage ? " has-image" : ""} ${className}`.trim()}
      style={style}
    >
      {!showImage && (
        <span aria-hidden="true" className="poster-art-placeholder">
          <ImageIcon size={24} strokeWidth={1.5} />
        </span>
      )}
      {!showImage && (
        <span className="sr-only">
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
