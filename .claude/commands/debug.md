Debug the reported issue autonomously.

Steps:
1. Reproduce the issue — run the failing command or test
2. Read error messages, stack traces, and logs carefully
3. Identify the root cause (not symptoms)
4. Search for related patterns in the codebase
5. Implement the fix — target minimal code change
6. Run the full validation pipeline (`/validate`)
7. Update `tasks/lessons.md` if this reveals a new pattern

Rules:
- Find the ROOT cause — don't patch symptoms
- Don't ask for hand-holding — just fix it
- If the fix feels hacky, step back and find the elegant solution
- Zero context switching required from the user
