"use client";

import Link from "next/link";
import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders an assistant message.
 *
 * Replies are markdown, because markdown is what a language model writes. An
 * earlier version matched links and bold with regexes on the assumption that
 * "only three constructs actually appear in these replies" — a Slack summary
 * with `###` headings, `>` quoted messages and `---` rules disproved it, and
 * showed the syntax to the user as literal text.
 *
 * `react-markdown` does not render raw HTML unless `rehype-raw` is added, so
 * model output cannot inject markup. That was the reason to avoid a parser
 * before, and it does not apply to this one.
 *
 * `remark-gfm` adds tables and strikethrough, which the agent reaches for when
 * summarising more than one item.
 */

type AnchorProps = ComponentPropsWithoutRef<"a">;

const LINK_CLASS =
  "font-medium text-primary underline underline-offset-2 hover:opacity-80";

function MarkdownLink({ href, children, ...props }: AnchorProps) {
  // Internal routes get client-side navigation; external ones open in a new
  // tab, since an OAuth flow should not replace the conversation.
  if (href?.startsWith("/")) {
    return (
      <Link href={href} className={LINK_CLASS}>
        {children}
      </Link>
    );
  }

  return (
    <a
      {...props}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={LINK_CLASS}
    >
      {children}
    </a>
  );
}

// Headings are levelled down: an assistant message sits inside the page, so its
// `###` is a bold line within the bubble rather than a document heading.
const COMPONENTS = {
  a: MarkdownLink,
  p: (props: ComponentPropsWithoutRef<"p">) => (
    <p {...props} className="mb-2 last:mb-0" />
  ),
  h1: (props: ComponentPropsWithoutRef<"h1">) => (
    <p {...props} className="mt-3 mb-1 font-semibold first:mt-0" />
  ),
  h2: (props: ComponentPropsWithoutRef<"h2">) => (
    <p {...props} className="mt-3 mb-1 font-semibold first:mt-0" />
  ),
  h3: (props: ComponentPropsWithoutRef<"h3">) => (
    <p {...props} className="mt-3 mb-1 font-semibold first:mt-0" />
  ),
  ul: (props: ComponentPropsWithoutRef<"ul">) => (
    <ul {...props} className="mb-2 list-disc space-y-1 pl-5 last:mb-0" />
  ),
  ol: (props: ComponentPropsWithoutRef<"ol">) => (
    <ol {...props} className="mb-2 list-decimal space-y-1 pl-5 last:mb-0" />
  ),
  // Quoted content is the answer, not an aside.
  //
  // This was text-muted-foreground, which is right for supporting text and
  // wrong here: when the user asks what a message said, the quote IS the
  // reply, and dimming it made the thing they asked for the hardest part to
  // read. The left border carries the "this is quoted" signal on its own.
  blockquote: (props: ComponentPropsWithoutRef<"blockquote">) => (
    <blockquote
      {...props}
      className="my-2 border-l-2 border-border pl-3 text-foreground"
    />
  ),
  hr: () => <hr className="my-3 border-border" />,
  code: (props: ComponentPropsWithoutRef<"code">) => (
    <code {...props} className="rounded bg-muted px-1 py-0.5 font-mono text-xs" />
  ),
  pre: (props: ComponentPropsWithoutRef<"pre">) => (
    <pre {...props} className="my-2 overflow-x-auto rounded bg-muted p-3 text-xs" />
  ),
  table: (props: ComponentPropsWithoutRef<"table">) => (
    <div className="my-2 overflow-x-auto">
      <table {...props} className="w-full text-left text-xs" />
    </div>
  ),
  th: (props: ComponentPropsWithoutRef<"th">) => (
    <th {...props} className="border-b border-border px-2 py-1 font-semibold" />
  ),
  td: (props: ComponentPropsWithoutRef<"td">) => (
    <td {...props} className="border-b border-border/50 px-2 py-1" />
  ),
} as const;

export function MessageText({ content }: { content: string }) {
  return (
    <div className="text-sm break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
