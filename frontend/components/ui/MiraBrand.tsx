import clsx from "clsx";
import Image from "next/image";

type MiraBrandProps = {
  className?: string;
};

export function MiraBrand({ className }: MiraBrandProps) {
  return (
    <div className={clsx("flex w-full items-start justify-center", className)}>
      <Image
        src="/mira-logo.png"
        alt="MIRA - Market Intelligence Research Architecture"
        width={931}
        height={490}
        priority
        sizes="(min-width: 768px) 266px, 238px"
        className="h-auto w-[238px] sm:w-[252px] md:w-[266px] drop-shadow-[0_12px_24px_rgba(0,113,227,0.08)]"
      />
    </div>
  );
}
