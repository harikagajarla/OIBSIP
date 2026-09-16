"""Small, dependency-free emoji shortcode replacement."""
REPLACEMENTS = {
    ":smile:": "😄", ":heart:": "❤️", ":thumbsup:": "👍", ":fire:": "🔥",
    ":)": "🙂", ":(": "🙁", ":D": "😄", ";)": "😉", "<3": "❤️",
}

def resolve_emoji(text: str) -> str:
    for shortcode in sorted(REPLACEMENTS, key=len, reverse=True):
        text = text.replace(shortcode, REPLACEMENTS[shortcode])
    return text
