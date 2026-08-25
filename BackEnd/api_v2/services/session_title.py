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


def compose_title(candidate_names: Optional[Iterable[str]], body: Optional[str]) -> str:
    """Put the selected respondents' names in front of `body`. Never returns ''.

    The names come from the caller's candidate list -- the checked respondents -- and never
    from the model. That is the point: the model used to write the whole title, names
    included, and it re-spelled them (游淑芬 -> 遊淑芬 in the 2026-08-24 client report,
    with `OpenCC('s2twp')` doing the same thing downstream). A name the backend supplies
    cannot be re-spelled by anything.

    Takes the name list rather than a pre-joined string so the 「無」 sentinel the route
    uses for the prompt cannot leak into a title.
    """
    names = join_names(candidate_names)
    b = ' '.join((body or '').split())

    if not b:
        # Nothing to show beside the names (an empty quick-question payload, a session
        # created before the first message, a model that returned only the name). Names
        # alone still beat a placeholder.
        return clamp_title(f'{names} 分析') if names else '未命名對話'

    prefix = f'{names}：' if names else ''
    room = TITLE_MAX - len(prefix)
    if room < MIN_QUERY_ROOM:
        prefix, room = '', TITLE_MAX
    return prefix + (b if len(b) <= room else b[:room - 1] + ELLIPSIS)


def fallback_title(candidate_names: Optional[Iterable[str]], user_query: Optional[str]) -> str:
    """A title that is always more informative than a placeholder. Never returns ''."""
    return compose_title(candidate_names, user_query)


# A head segment is treated as names when this share of its Chinese characters also occur
# in the candidate list. Not an exact match, because the case worth catching is the model
# writing its *own* spelling of a name: 「遊淑芬」 overlaps 游淑芬 by 2/3. An unrelated head
# such as 「溝通模式」 overlaps by 0, so it survives.
NAME_HEAD_OVERLAP = 0.6

# Characters that can sit between a name segment and the theme once the name is removed.
_NAME_TRAILERS = '：:，,、 　的與和及'


def _looks_like_names(head: str, name_chars: set) -> bool:
    cjk = [c for c in head if '一' <= c <= '鿿']
    if not cjk or not name_chars:
        return False
    return sum(c in name_chars for c in cjk) / len(cjk) >= NAME_HEAD_OVERLAP


def strip_model_names(theme: Optional[str],
                      candidate_names: Optional[Iterable[str]]) -> str:
    """Remove respondents' names from the model's output so `compose_title` owns them.

    The prompt asks for the analysis theme alone. A model that ignores that would otherwise
    give 「游淑芬：游淑芬的抗壓性」 -- or, worse, its own spelling of the name in the body,
    which is the defect this whole path exists to stop. Two passes:

      * a leading 「<names>：」 segment, matched by character overlap rather than equality
      * any candidate name still sitting at the front, with its trailing particle

    Returns '' when nothing but the name was returned; the caller treats that as the model
    having produced no title, which is the correct reading.
    """
    t = ' '.join((theme or '').split())
    name_chars = {c for n in (candidate_names or []) if n for c in n}

    for colon in ('：', ':'):
        head, sep, tail = t.partition(colon)
        if sep and tail.strip() and _looks_like_names(head, name_chars):
            t = tail.strip()
            break

    shrinking = True
    while shrinking:
        shrinking = False
        for name in sorted({n for n in (candidate_names or []) if n}, key=len, reverse=True):
            # Overlap again rather than startswith: 「遊淑芬的抗壓性分析」 has no colon to
            # split on and never equals 游淑芬, but its first three characters are still
            # the model's spelling of the name and must not reach the title.
            if _looks_like_names(t[:len(name)], set(name)):
                t = t[len(name):].lstrip(_NAME_TRAILERS)
                shrinking = True
    return t.strip()


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
