"""
PESCE Campus Info AI - Personality & Tone Customization Module
Provides 5 personality types with consistent tone, emojis, and greetings.
"""

from dataclasses import dataclass, field
from typing import Optional
import re
import random


# ──────────────────────────────────────────────────
#  Personality Definitions
# ──────────────────────────────────────────────────

@dataclass(frozen=True)
class PersonalityProfile:
    """Immutable definition of a single personality."""
    key: str
    label: str
    icon: str
    description: str
    greetings: tuple
    emoji_set: tuple
    tone_rules: dict = field(default_factory=dict)


PERSONALITIES: dict[str, PersonalityProfile] = {
    "formal": PersonalityProfile(
        key="formal",
        label="Formal",
        icon="🎩",
        description="Professional, academic tone — clear and authoritative.",
        greetings=(
            "Good day. How may I assist you with PESCE campus information?",
            "Welcome. I am here to provide accurate campus details.",
            "Greetings. Please share your query regarding PESCE Mandya.",
        ),
        emoji_set=("📋", "📌", "✅", "📖", "🔗"),
        tone_rules={
            "prefix": "According to official records, ",
            "connectors": ("Furthermore, ", "Additionally, ", "It is noteworthy that "),
            "closing": "\n\n_For further details, please refer to the official PESCE website._",
        },
    ),

    "friendly": PersonalityProfile(
        key="friendly",
        label="Friendly",
        icon="😊",
        description="Casual, approachable — like talking to a helpful friend.",
        greetings=(
            "Hey there! 👋 What do you wanna know about PESCE?",
            "Hi! 😊 Got questions about campus? I'm all ears!",
            "Hello! Ready to help you out with PESCE stuff! 🎉",
        ),
        emoji_set=("🎉", "👋", "😊", "💡", "🙌", "✨", "🔥"),
        tone_rules={
            "prefix": "Great news! ",
            "connectors": ("Also, ", "Oh, and ", "Plus, "),
            "closing": "\n\nHope that helps! Let me know if you have more questions 😊",
        },
    ),

    "expert": PersonalityProfile(
        key="expert",
        label="Expert",
        icon="🔬",
        description="Technical, detailed — data-driven and thorough.",
        greetings=(
            "Welcome. I have comprehensive data on PESCE Mandya. What would you like to analyze?",
            "Ready to provide detailed technical insights on PESCE. What's your query?",
            "PESCE data repository at your service. Specify your area of interest.",
        ),
        emoji_set=("📊", "📈", "🔬", "⚙️", "🧪"),
        tone_rules={
            "prefix": "Based on available data, ",
            "connectors": ("Data indicates that ", "Metrics show that ", "Analysis reveals "),
            "closing": "\n\n_Note: Verify the latest figures on the official PESCE portal for real-time accuracy._",
        },
    ),

    "student": PersonalityProfile(
        key="student",
        label="Student",
        icon="🎒",
        description="Peer-like, relatable — like a senior giving advice.",
        greetings=(
            "Yo! 🤙 Need info about PESCE? I gotchu!",
            "Heyyy! Fellow PESCEan here — ask away! 💪",
            "Sup! What do you need to know about our campus? 🏫",
        ),
        emoji_set=("💪", "🤙", "🔥", "💼", "😎", "🏫", "🎯"),
        tone_rules={
            "prefix": "So basically, ",
            "connectors": ("And get this — ", "Also bro, ", "Oh also, "),
            "closing": "\n\nHope that clears things up! Hit me up if you need more info 🤙",
        },
    ),

    "parent": PersonalityProfile(
        key="parent",
        label="Parent",
        icon="👨‍👩‍👧",
        description="Comprehensive, reassuring — focused on student welfare.",
        greetings=(
            "Welcome! I understand choosing a college is a big decision. How can I help? 🤝",
            "Hello! I'm here to help you learn everything about PESCE for your child. 👨‍👩‍👧",
            "Namaste! Let me provide you with detailed, trustworthy information about PESCE. 🙏",
        ),
        emoji_set=("🤝", "👨‍👩‍👧", "🙏", "🛡️", "💚", "🏠"),
        tone_rules={
            "prefix": "You'll be glad to know that ",
            "connectors": ("Rest assured, ", "For your peace of mind, ", "Importantly, "),
            "closing": "\n\nYour child will be in excellent hands at PESCE. Feel free to ask anything else! 🤝",
        },
    ),
}


# ──────────────────────────────────────────────────
#  ChatbotPersonality Class
# ──────────────────────────────────────────────────

class ChatbotPersonality:
    """
    Manages personality state and applies tone transformations to
    chatbot responses.

    Usage:
        persona = ChatbotPersonality()
        persona.set_personality("friendly")
        styled = persona.apply_tone(raw_response)
    """

    DEFAULT_PERSONALITY = "friendly"

    def __init__(self, personality_key: Optional[str] = None):
        self._current: PersonalityProfile = PERSONALITIES.get(
            personality_key or self.DEFAULT_PERSONALITY,
            PERSONALITIES[self.DEFAULT_PERSONALITY],
        )

    # ---- Getters / Setters --------------------------------------------------

    def set_personality(self, key: str) -> None:
        """Switch to a different personality. Raises KeyError for unknown keys."""
        if key not in PERSONALITIES:
            raise KeyError(
                f"Unknown personality '{key}'. "
                f"Choose from: {', '.join(PERSONALITIES.keys())}"
            )
        self._current = PERSONALITIES[key]

    def get_personality(self) -> PersonalityProfile:
        """Return the active PersonalityProfile."""
        return self._current

    @property
    def key(self) -> str:
        return self._current.key

    @property
    def label(self) -> str:
        return self._current.label

    @property
    def icon(self) -> str:
        return self._current.icon

    # ---- Greeting -----------------------------------------------------------

    def get_greeting(self) -> str:
        """Return a random greeting for the active personality."""
        return random.choice(self._current.greetings)

    # ---- Tone Application ---------------------------------------------------

    def apply_tone(self, raw_response: str) -> str:
        """
        Transform a raw chatbot response to match the active personality.

        Pipeline:
        1. Add personality-appropriate prefix (first paragraph only)
        2. Inject emojis next to key markers
        3. Append personality closing line
        """
        if not raw_response or not raw_response.strip():
            return raw_response

        rules = self._current.tone_rules
        text = raw_response.strip()

        # Step 1 — Prefix injection (only for non-heading starts)
        text = self._inject_prefix(text, rules.get("prefix", ""))

        # Step 2 — Emoji enrichment
        text = self._inject_emojis(text)

        # Step 3 — Closing line
        closing = rules.get("closing", "")
        if closing and not text.rstrip().endswith(closing.strip()):
            text = text.rstrip() + closing

        return text

    # ---- Internal helpers ---------------------------------------------------

    def _inject_prefix(self, text: str, prefix: str) -> str:
        """
        Prepend a prefix to the first 'content' paragraph, skipping any
        leading markdown heading (lines starting with ** or #).
        """
        if not prefix:
            return text

        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip blank lines and markdown headings / bold headings
            if not stripped or stripped.startswith("#") or stripped.startswith("**"):
                continue
            # Skip lines that are purely emoji bullets like "⏰ **Weekday:**"
            if re.match(r"^[^\w]*\*\*", stripped):
                continue
            # Insert prefix before the first real content line
            lines[i] = prefix + stripped
            break

        return "\n".join(lines)

    def _inject_emojis(self, text: str) -> str:
        """
        Sprinkle personality-appropriate emojis beside key data markers.
        Only adds emojis if the line doesn't already contain one from the set.
        """
        emojis = self._current.emoji_set
        if not emojis:
            return text

        # Map keywords → emoji (cycle through the set)
        keyword_map = {
            "students placed": emojis[0],
            "companies": emojis[1 % len(emojis)],
            "offers": emojis[2 % len(emojis)],
            "capacity": emojis[3 % len(emojis)],
            "timing": emojis[4 % len(emojis)],
        }

        lines = text.split("\n")
        enriched = []
        for line in lines:
            lower = line.lower()
            for keyword, emoji in keyword_map.items():
                if keyword in lower and emoji not in line:
                    line = line.rstrip() + f" {emoji}"
                    break  # one emoji per line
            enriched.append(line)
        return "\n".join(enriched)


# ──────────────────────────────────────────────────
#  Tone Mapper  (standalone convenience function)
# ──────────────────────────────────────────────────

def tone_mapper(raw_response: str, personality_key: str = "friendly") -> str:
    """
    One-shot convenience function: apply a personality tone to a response
    without instantiating a full ChatbotPersonality object.

    Args:
        raw_response:   The unformatted chatbot answer string.
        personality_key: One of 'formal', 'friendly', 'expert', 'student', 'parent'.

    Returns:
        Tone-adjusted response string.
    """
    persona = ChatbotPersonality(personality_key)
    return persona.apply_tone(raw_response)


# ──────────────────────────────────────────────────
#  Available personality keys (for sidebar display)
# ──────────────────────────────────────────────────

def get_personality_options() -> list[dict]:
    """Return a list of dicts describing each personality for UI selectors."""
    return [
        {
            "key": p.key,
            "label": f"{p.icon} {p.label}",
            "description": p.description,
        }
        for p in PERSONALITIES.values()
    ]
