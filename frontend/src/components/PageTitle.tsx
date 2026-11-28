import { forwardRef } from "react";

/**
 * Two-tone page heading: the lead words in paper white, the final words in
 * lavender. Screen readers get one continuous heading.
 */
export const PageTitle = forwardRef<
  HTMLHeadingElement,
  {
    lead: string;
    accent?: string;
    className?: string;
    focusable?: boolean;
  }
>(function PageTitle({ lead, accent, className = "", focusable }, ref) {
  return (
    <h1
      className={`page-title ${className}`.trim()}
      ref={ref}
      tabIndex={focusable ? -1 : undefined}
    >
      {lead}
      {accent && (
        <>
          {" "}
          <span className="accent">{accent}</span>
        </>
      )}
    </h1>
  );
});
