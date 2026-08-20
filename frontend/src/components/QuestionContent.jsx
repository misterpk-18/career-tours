import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createLowlight } from 'lowlight';
import bash from 'highlight.js/lib/languages/bash';
import c from 'highlight.js/lib/languages/c';
import cpp from 'highlight.js/lib/languages/cpp';
import csharp from 'highlight.js/lib/languages/csharp';
import css from 'highlight.js/lib/languages/css';
import dockerfile from 'highlight.js/lib/languages/dockerfile';
import http from 'highlight.js/lib/languages/http';
import ini from 'highlight.js/lib/languages/ini';
import java from 'highlight.js/lib/languages/java';
import javascript from 'highlight.js/lib/languages/javascript';
import json from 'highlight.js/lib/languages/json';
import markdown from 'highlight.js/lib/languages/markdown';
import nginx from 'highlight.js/lib/languages/nginx';
import powershell from 'highlight.js/lib/languages/powershell';
import python from 'highlight.js/lib/languages/python';
import sql from 'highlight.js/lib/languages/sql';
import typescript from 'highlight.js/lib/languages/typescript';
import xml from 'highlight.js/lib/languages/xml';
import { cn } from '../lib/cn';

// Exactly the languages the corpus uses, registered one at a time.
//
// This is lowlight directly rather than rehype-highlight, and the reason is
// measured: rehype-highlight statically imports lowlight's `common` bundle
// (~35 grammars) whether you pass it a language list or not, so the list cannot
// make it smaller — it only adds. Production bundle, same page:
//
//   baseline (no markdown at all)               353 KB
//   + react-markdown / remark-gfm               530 KB
//   + rehype-highlight (common, unavoidable)    708 KB
//   + an 18-language list on top of that        779 KB   <- worse, not better
//
// Registering these grammars against a bare lowlight instance ships only what
// the corpus can actually contain.
//
// Eleven of the corpus's 29 fence languages have no grammar here and render as
// plain monospace with their indentation intact: `text` (1,249 blocks — ledger
// extracts, trial balances, report output, which have no language by design),
// plus csv, dax, powerquery, vba and terraform, which highlight.js either does
// not ship or needs a plugin for. Losing colour on a trial balance costs
// nothing; shipping 355KB on every page load to get it is not free.
//
// Aliases come from the grammars themselves, so `xml` covers html, `javascript`
// covers jsx, and `typescript` covers tsx — which is why those three are not
// listed separately.
const lowlight = createLowlight({
  bash,
  c,
  cpp,
  csharp,
  css,
  dockerfile,
  http,
  ini,
  java,
  javascript,
  json,
  markdown,
  nginx,
  powershell,
  python,
  sql,
  typescript,
  xml,
});

/**
 * lowlight returns a hast tree; walk it into React elements.
 *
 * Deliberately not `hast-util-to-html` with dangerouslySetInnerHTML. The escape
 * correctness would be lowlight's rather than ours, and a highlighter is not
 * where the safety of a page that renders 2,560 generated strings should rest.
 * Ten lines of recursion avoids the question entirely.
 */
const renderHast = (node, key) => {
  if (node.type === 'text') return node.value;
  if (node.type !== 'element') return null;

  return React.createElement(
    node.tagName,
    { key, className: node.properties?.className?.join(' ') },
    node.children?.map((child, i) => renderHast(child, i))
  );
};

/**
 * A question's text: prose, fenced code blocks, and inline identifiers.
 *
 * 1,495 of the corpus's 1,600 MCQs carry a code or data artefact, and the
 * generator was held to a formatting contract for exactly this surface: every
 * artefact in a fenced block with a language tag, single backticks for an
 * identifier mentioned mid-sentence, and no other markdown. So the component
 * map below is not a subset of what markdown can do — it is the whole set of
 * things the corpus is allowed to contain.
 *
 * Anything outside that set is still rendered rather than dropped, because a
 * silently missing sentence is worse than an unstyled one. But nothing here
 * assumes headings or tables will appear, since the contract forbids them.
 *
 * The language label is worth showing. A stem that hands you a trial balance
 * and one that hands you a SQL schema are read differently, and the tag is the
 * only thing that says which before you start reading.
 */

// Highlight.js emits .hljs-* class names; the theme for them lives in
// index.css and is built from the app's own palette rather than imported from
// highlight.js/styles. Two reasons: the app has a real dark mode driven by
// [data-theme], and shipping github.css plus github-dark.css would mean two
// stylesheets fighting over the same class names with no theme awareness.
const CodeBlock = ({ className, children }) => {
  const language = /language-(\w+)/.exec(className || '')?.[1];

  // Trailing newline: markdown always leaves one before the closing fence, and
  // rendering it adds a blank line inside every single block.
  const code = String(children).replace(/\n$/, '');

  // An unregistered language is shown as-is. It must not throw — dax and
  // powerquery are real content in this corpus, not a mistake.
  const highlighted =
    language && lowlight.registered(language) ? lowlight.highlight(language, code) : null;

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-line bg-surface-2">
      {language ? (
        <div className="flex items-center justify-between border-b border-line px-3 py-1.5">
          <span className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">
            {language}
          </span>
        </div>
      ) : null}
      {/* The pre scrolls, not the page: a 90-character SQL line must not make
          the whole question card scroll sideways. */}
      <pre className="overflow-x-auto p-3 text-[13px] leading-relaxed">
        <code className={cn('font-mono', language && `language-${language}`)}>
          {highlighted ? highlighted.children.map((child, i) => renderHast(child, i)) : code}
        </code>
      </pre>
    </div>
  );
};

const COMPONENTS = {
  // react-markdown hands both inline and fenced code to `code`; only the fenced
  // one is wrapped in a `pre`, which is where the distinction has to be made.
  pre: ({ children }) => <>{children}</>,
  code: ({ node, inline, className, children, ...props }) => {
    const isFenced = /language-/.test(className || '') || String(children).includes('\n');

    if (!isFenced) {
      return (
        <code
          className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[0.9em] text-fg"
          {...props}
        >
          {children}
        </code>
      );
    }

    return <CodeBlock className={className}>{children}</CodeBlock>;
  },
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  a: ({ children, href }) => (
    <a href={href} className="text-brand-fg underline" target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  // Not expected — the contract bans both — but rendered legibly if a future
  // corpus ever emits one, rather than falling back to browser defaults that
  // ignore the palette entirely.
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-line bg-surface-2 px-2 py-1 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border border-line px-2 py-1">{children}</td>,
};

export const QuestionContent = ({ children, className }) => {
  if (!children) return null;

  return (
    <div className={cn('text-[15px] leading-relaxed text-fg', className)}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={COMPONENTS}
      >
        {children}
      </Markdown>
    </div>
  );
};

export default QuestionContent;
