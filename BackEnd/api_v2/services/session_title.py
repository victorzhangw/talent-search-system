"""Deterministic conversation titles, used when the model cannot supply one.

The history list used to show 「新對話」 whenever the title call came back with empty
content, and `background_generate_title` then wrote that literal string into
`metadata['title']`. Two things followed from that:

  * `GET /sessions` has its own fallback (candidate names + 「 分析」), but it only fires
    when `title` is unset -- writing 「新對話」 as the title suppressed it.
  * `title` being set meant the session was never retried, so the placeholder was
    permanent.

The observed trigger was the reasoning pass eating the whole `max_tokens` budget: every
failure in conversations.log sits at exactly C:200, every success below it. That is fixed
at the call site by disabling thinking; this module is the safety net for whatever still
gets through, and it is good enough to use as the *initial* title too, written
synchronously when the session is created so no placeholder is ever displayed.

Why the user's own text is the right fallback:

  快速提問 arrives with the curated question label (useChatLogic.sendQuickMessage sends
  `questionItem.label`), which already reads like the title the prompt asks the model for.
  自由提問 arrives with whatever the user typed -- and their own question is the thing they
  will recognise fastest in a history list. Neither needs a model.
"""

from typing import Iterable, Optional

# The 20-character ceiling is the rule the LLM path already applied; keeping it here
# means the two paths cannot drift apart.
TITLE_MAX = 20
ELLIPSIS = '…'

# What the old code wrote into metadata['title'] when the model returned nothing. It is
# treated as *absent* everywhere rather than as a title: sessions written before this
# module existed still carry it, and re-displaying it would make the fix invisible to
# exactly the users who hit the bug. Never write this string.
LEGACY_PLACEHOLDER = '新對話'


def is_placeholder(title: Optional[str]) -> bool:
    """True when `title` carries no information and should be replaced."""
    return not (title or '').strip() or (title or '').strip() == LEGACY_PLACEHOLDER

# Below this many characters the question is unreadable, so the names are dropped instead:
# four respondents already spend 17 characters, and a title that is a list of names ending
# in an ellipsis identifies nothing. Which question it was is the more useful half.
MIN_QUERY_ROOM = 8


def clamp_title(title: Optional[str]) -> str:
    """Collapse whitespace and cut to TITLE_MAX, marking the cut."""
    t = ' '.join((title or '').split())
    return t if len(t) <= TITLE_MAX else t[:TITLE_MAX - 1] + ELLIPSIS


def join_names(candidate_names: Optional[Iterable[str]]) -> str:
    return ', '.join(n for n in (candidate_names or []) if n)


def fallback_title(candidate_names: Optional[Iterable[str]], user_query: Optional[str]) -> str:
    """A title that is always more informative than a placeholder. Never returns ''.

    Takes the name list rather than a pre-joined string so the 「無」 sentinel the route
    used for the prompt cannot leak into a title.
    """
    names = join_names(candidate_names)
    q = ' '.join((user_query or '').split())

    if not q:
        # No question to show (an empty quick-question payload, or a session created
        # before the first message). Names alone still beat a placeholder.
        return clamp_title(f'{names} 分析') if names else '未命名對話'

    prefix = f'{names}：' if names else ''
    room = TITLE_MAX - len(prefix)
    if room < MIN_QUERY_ROOM:
        prefix, room = '', TITLE_MAX
    return prefix + (q if len(q) <= room else q[:room - 1] + ELLIPSIS)


def title_for_metadata(metadata: Optional[dict]) -> str:
    """What the history list should display for a session, from its metadata alone.

    Used by GET /sessions, which sees rows the title thread never touched: 117 of the 228
    sessions on the dev box have no metadata at all, and another 24 have the legacy
    placeholder saved as their title. Both used to render as 「新對話」.
    """
    meta = metadata if isinstance(metadata, dict) else {}
    saved = (meta.get('title') or '').strip()
    if is_placeholder(saved):
        saved = ''
    names = [c.get('name') for c in (meta.get('candidates') or [])
             if isinstance(c, dict) and c.get('name')]
    return saved or fallback_title(names, '')
