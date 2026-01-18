# process.py
# Core processing / business logic layer

def run(payload: dict) -> dict:
    text = payload.get("input")

    if not text:
        return {
            "status": "error",
            "message": "No input provided"
        }

    word_count = len(text.split())
    risk_flags = []

    if word_count < 50:
        risk_flags.append("Too little detail")
    if "budget" not in text.lower():
        risk_flags.append("No budget mentioned")
    if "timeline" not in text.lower():
        risk_flags.append("No timeline mentioned")

    return {
        "status": "processed",
        "summary": text[:300],
        "metrics": {
            "chars": len(text),
            "words": word_count
        },
        "strengths": [
            "Clear intent" if word_count > 50 else "Concise idea"
        ],
        "risks": risk_flags,
        "next_steps": [
            "Expand project description",
            "Add budget section",
            "Define timeline"
        ]
    }
