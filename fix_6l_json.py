#!/usr/bin/env python3
"""Fix broken JSON from 6L extraction"""

import json
import re
from pathlib import Path

input_file = Path("data/processed/gemini_ultra/6L_raw_attempt.txt")
output_file = Path("data/processed/gemini_ultra/6L_gemini.json")

print("Attempting to fix 6L JSON...")

with open(input_file, 'r', encoding='utf-8') as f:
    raw_text = f.read()

print(f"Raw text length: {len(raw_text)} chars")
print(f"Lines: {len(raw_text.splitlines())}")

# Try 1: Fix unterminated strings and add closing bracket
attempts = [
    # Just add closing bracket
    lambda t: t + "]" if not t.endswith("]") else t,

    # Remove incomplete last object and close
    lambda t: re.sub(r',\s*\{[^}]*$', '\n]', t),

    # Find last complete object and close there
    lambda t: t[:t.rfind('}')+1] + '\n]' if '}' in t else t,
]

for i, fix_func in enumerate(attempts, 1):
    try:
        print(f"\nAttempt {i}...")
        fixed_text = fix_func(raw_text)

        # Try to parse
        events = json.loads(fixed_text)

        print(f"SUCCESS! Parsed {len(events)} events")

        # Validate events
        valid_events = []
        for event in events:
            if isinstance(event, dict) and event.get('year') is not None:
                valid_events.append(event)

        print(f"Valid events: {len(valid_events)}")

        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(valid_events, f, ensure_ascii=False, indent=2)

        print(f"Saved to: {output_file}")
        print(f"\nSample events:")
        for event in valid_events[:3]:
            print(f"  - {event.get('year')}: {event.get('title')}")

        break

    except json.JSONDecodeError as e:
        print(f"  Failed: {e}")
        continue
    except Exception as e:
        print(f"  Error: {e}")
        continue
else:
    print("\nAll fix attempts failed. Manual intervention needed.")

    # Show last part of file
    print("\nLast 500 chars:")
    print(raw_text[-500:])
