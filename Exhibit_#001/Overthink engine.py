"""Overthink Engine — a tiny spiral of second-guessing."""

from __future__ import annotations

import random
import sys
import time


THOUGHTS_EARLY = [
    "Though this be madness, yet there is method in't...",
    "Expectation is the root of my headache...",
    "Re-evaluating assumptions...",
    "Checking consistency...",
    "This might work... until it doesn't...",
    "Flickering through the reasoning again...",
    "This still feels incomplete...",
    "What if there's another interpretation?",
]

THOUGHTS_MID = [
    "Wait — did I already consider that angle?",
    "The first answer looked fine. Suspiciously fine.",
    "Looping back to premises I thought were settled...",
    "Confidence dipping. Curiosity climbing.",
    "If this were simple, I wouldn't still be here...",
    "Rewinding the chain of 'therefore's...",
    "There's a quieter objection I haven't named yet...",
    "Method intact. Sanity negotiable.",
]

THOUGHTS_LATE = [
    "Okay but what if the opposite is also true?",
    "I'm arguing with a version of myself from three spirals ago...",
    "Every clarification opens two new questions...",
    "The footnotes are writing footnotes...",
    "Certainty left the chat. I'm still typing.",
    "This conclusion has trust issues.",
    "Rebuilding the argument from a slightly worse angle...",
    "Neurons filing a formal complaint...",
]


def ask_cycles() -> int:
    """Prompt until the user enters a positive integer."""
    while True:
        raw = input("How many spirals should the engine run? ").strip()
        try:
            cycles = int(raw)
        except ValueError:
            print("Please enter a positive integer.")
            continue
        if cycles < 1:
            print("Please enter a positive integer.")
            continue
        return cycles


def pick_thought(progress: float) -> str:
    """Choose a thought that grows more frantic as the run progresses."""
    if progress < 0.34:
        pool = THOUGHTS_EARLY
    elif progress < 0.67:
        pool = THOUGHTS_EARLY + THOUGHTS_MID
    else:
        pool = THOUGHTS_MID + THOUGHTS_LATE
    return random.choice(pool)


def pause(seconds: float) -> None:
    """Sleep, but stay responsive to Ctrl+C."""
    time.sleep(seconds)


def overthink(spirals: int) -> None:
    print()
    print("Overthink Engine online.")
    print(f"Initiating {spirals} spiral{'s' if spirals != 1 else ''} of doubt...")
    print()
    pause(0.8)

    for spiral in range(1, spirals + 1):
        progress = spiral / spirals
        thought = pick_thought(progress)
        print(f"Spiral {spiral}/{spirals}: {thought}")

        # Slightly faster as frustration mounts — still deliberate.
        delay = 1.6 - (0.5 * progress)
        pause(delay)

    print()
    pause(1.2)
    print("System update: Frustration level rising. Intercepting thoughts...")
    pause(2.2)
    print("Nope. Fried my neurons.")
    print()


def main() -> int:
    try:
        cycles = ask_cycles()
        overthink(cycles)
    except KeyboardInterrupt:
        print("\n\nEmergency exit: spiral aborted mid-thought.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
