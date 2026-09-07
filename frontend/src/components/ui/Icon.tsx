import type { FC } from "react";

type IconName =
  | "location"
  | "progress"
  | "review"
  | "lesson"
  | "map"
  | "clock"
  | "chevron"
  | "check"
  | "alert";

const paths: Record<IconName, string> = {
  location: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
  progress: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z",
  review: "M12 5V2L10 4l2 2v-3c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8L19.29 19 21 20.71l-4-4c-.83.45-1.79.7-2.79.7-3.31 0-6-2.69-6-6s2.69-6 6-6zm6.79 1.71l-4 4V14c0 2.21-1.79 4-4 4S8 16.21 8 14s1.79-4 4-4v2.71l4-4c.79.79 1.79 1.58 2.79 2.29z",
  lesson: "M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z",
  map: "M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-3-1.05-3 1.05V4.95l3 1.05 3-1.05V19z",
  clock: "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z",
  chevron: "M8.59 16.59l4.58-4.59-4.58-4.59L10 5.83l6 6-6 6z",
  check: "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
  alert: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
};

interface Props {
  name: IconName;
  size?: number;
  className?: string;
  "aria-hidden"?: boolean;
}

const Icon: FC<Props> = ({ name, size = 16, className = "", "aria-hidden": ariaHidden = true }) => {
  const path = paths[name];
  if (!path) return null;

  return (
    <svg
      className={`sq-icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={ariaHidden}
      style={{ "--size": `${size}px` } as React.CSSProperties}
    >
      <path d={path} />
    </svg>
  );
};

export default Icon;