import { useEffect, useState } from "react";

const duration = 1000;

/** 結果の登場時だけ再生し、離脱・動きの低減設定では即座に停止する。 */
export function useEntranceProgress() {
  const [progress, setProgress] = useState(() =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : 0,
  );

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    const started = performance.now();
    function finishIfReduced() {
      if (preference.matches) {
        cancelAnimationFrame(frame);
        setProgress(1);
      }
    }
    function animate(now: number) {
      const elapsed = Math.min(1, (now - started) / duration);
      setProgress(1 - Math.pow(1 - elapsed, 3));
      if (elapsed < 1) frame = requestAnimationFrame(animate);
    }
    if (!preference.matches) frame = requestAnimationFrame(animate);
    preference.addEventListener("change", finishIfReduced);
    return () => {
      cancelAnimationFrame(frame);
      preference.removeEventListener("change", finishIfReduced);
    };
  }, []);

  return progress;
}
