import { BookOpen } from "lucide-react";
import { Chips } from "@/components/citations/CitationChip";
import { RichText } from "@/components/common/RichText";
import { Panel, Section } from "@/components/common/Section";
import type { Brief } from "@/lib/types";

export function StorySoFar({ story }: { story: Brief["story"] }) {
  return (
    <Section icon={BookOpen} title="Story so far">
      <Panel>
        {story.length === 0 ? <p className="text-muted-foreground">No story yet — run the digest.</p> : (
          <ol className="space-y-3.5 border-l pl-5">
            {story.map((s, i) => (
              <li key={i} className="relative max-w-prose text-[14px] leading-relaxed before:absolute before:-left-[25px] before:top-2 before:size-1.5 before:rounded-full before:bg-primary/70">
                <RichText text={s.text} /><Chips citations={s.citations} />
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </Section>
  );
}
