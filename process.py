# process.py
# Core processing / business logic layer

def run_process(input_data: str) -> dict:
    if not input_data:
        return {
            "status": "error",
            "message": "No input provided"
        }

    return {
        "input": input_data,
        "chars": len(input_data),
        "status": "processed"
    }
