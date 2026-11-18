# AI Usage Documentation

## Overview

I built this project together with an AI coding assistant. The work split was roughly **70% AI and 30% me**. I set up the project, made the design decisions, configured the database, directed each step, and tested and reviewed the results. The AI generated code from my prompts and the project specification.

## Tools Used

- **Cursor** (an AI code editor) with **Claude** as the coding agent. I used it to:
  - plan the build and break it into milestones
  - generate the SQL schema, the Flask routes, the database functions, and the HTML templates
  - debug setup problems and explain error messages
  - write the README setup instructions

## What I Did

- **Set up the project.** I created the GitHub repository, wrote the first README, and added the project specification to the folder so the AI could work from it.
- **Defined the requirements.** I gave the AI the assignment description and the specification, and checked that its plan covered the four tables, CRUD on every table, the dashboard, and Job Match.
- **Made the design decisions.** I chose Bootstrap 5 with a custom stylesheet for the UI. I also chose to commit and push after each milestone so the history shows the project being built step by step.
- **Configured MySQL.** I set up the local MySQL 8.0 server. When the root password didn't work, I reset it from an Administrator PowerShell so the app could connect.
- **Tested and reviewed the work.** I ran the app after each milestone and checked that the pages, forms, validation, and Job Match results worked against my database.
- **Asked for changes.** After the main build, I asked for setup to be made easier for someone cloning the repo. That led to `setup_db.py` and the clearer error messages.
- **Recorded the demo video** and wrote this document.

## Key Prompts

1. *"Course Project: Job Application Tracker ... Build a complete web application that helps users track their job applications"* (followed by the full assignment description).
2. *"Ok I put the doc in, formulate a plan and get started."*
3. *"Implement the plan as specified."* The plan had milestones for the schema, each table's CRUD, the dashboard, Job Match, and polish.
4. *"Is the project connected to the GitHub repo?"* and *"Is everything committed to GitHub?"*
5. *"Are the steps for the instructor to view this easy on the repo?"*
6. *"Add whatever you think might be easy for them to set up so they won't have trouble."*

## What Worked Well

- **Fast scaffolding.** The AI produced the schema, the CRUD routes, and the templates for all four tables quickly and consistently.
- **The JSON columns.** It stored job requirements (skills, experience, education) and interview rounds as JSON, and used MySQL's `JSON_TABLE` for the dashboard statistics.
- **The Job Match algorithm.** It compares my skills against each job's required skills without regard to letter case, ranks jobs by match percentage, and lists the missing skills, matching the example in the spec.
- **Validation.** Server-side checks cover required fields, ENUM values, salary ranges, emails, phone numbers, URLs, and dates.
- **Debugging help.** When MySQL rejected the connection, it worked out that the password was the problem and gave me step-by-step reset commands.
- **Small commits.** Each milestone became its own commit with a clear message.

## What I Modified or Directed

- **Styling.** I picked Bootstrap 5 plus a custom `style.css` instead of only plain CSS.
- **Database credentials.** I made sure the MySQL password lives in a `.env` file that git ignores, so it is never pushed to GitHub.
- **Easier setup.** The first version required running `schema.sql` by hand, which fails in Windows PowerShell because `<` isn't supported and `mysql` often isn't on the PATH. I asked for a simpler path, which became `setup_db.py`, a Quick start section, and a troubleshooting table in the README.
- **Clearer errors.** If the database is misconfigured, the app now says exactly what to fix instead of showing a stack trace.

## Lessons Learned

- **Test everything the AI writes.** The code looked right, but I only trusted it once I had run it against my own database.
- **Specific prompts get better results.** Giving the AI the full specification produced a plan that matched the rubric much more closely than a vague request would have.
- **The AI can't do everything.** It couldn't reset my MySQL password or open an Administrator PowerShell, so I had to handle environment setup myself.
- **Plan in milestones.** Breaking the work into steps made the AI's output easier to review and gave the project a clean commit history.
- **Think about the person running it.** Making the app easy to set up on another computer took as much thought as making it work on mine.
