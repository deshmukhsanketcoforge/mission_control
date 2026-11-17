"""Helpers for building prompts from untrusted text."""


def untrusted_block(tag: str, text: str) -> str:
    """Wrap untrusted text in ``<tag>...</tag>``.

    Angle brackets inside the text are escaped, so the text cannot close the
    block early and pass its own words off as instructions.
    """
    safe = text.replace("<", "&lt;").replace(">", "&gt;")
    return f"<{tag}>\n{safe}\n</{tag}>"
