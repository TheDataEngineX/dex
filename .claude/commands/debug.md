Debug the reported issue autonomously.

Steps:

1. Reproduce the issue — run the failing command or test
1. Read error messages, stack traces, and logs carefully
1. Identify the root cause (not symptoms)
1. Search for related patterns in the codebase
1. Implement the fix — target minimal code change
1. Run the full validation pipeline (`/validate`)
1. Update `tasks/lessons.md` if this reveals a new pattern

Rules:

- Find the ROOT cause — don't patch symptoms
- Don't ask for hand-holding — just fix it
- If the fix feels hacky, step back and find the elegant solution
- Zero context switching required from the user
