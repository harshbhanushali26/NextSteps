"""
NextSteps — AI Career Automation Agent

Entry point for local development.
Run: python main.py  (or: uvicorn api.main:app --reload)
"""
import uvicorn


def main():
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
