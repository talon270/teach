# Teach, Monsoon 2026
Lessons, reference pages, drills and notes for each course. Open `index.html` (landing page) or `plan.html` (day plan).
The landing page opens on a Today card: today's tasks from the day plan, the dated tests, and how many core items from earlier days are not ticked. A tick there is the same tick as in the day plan (one `localStorage` key). The day plan folds the days before today and marks today.
Every page except the landing page has a bar at the top and the bottom: Back (the previous page, or one level up when you opened the page directly), the course map, and All courses. `build.py` step 6 adds it at publish time; the source pages stay untouched.
Test dates live in `EXAMS` in `study/_context/build/teach/plan.py`; add the other exams there when their dates are known.
Layout: `<COURSE>/` for lessons, `notes/<COURSE>/` for study notes and drills.
The pages are mirrored from the local study folder by `publish.sh`, which also rebuilds `index.html`. Do not edit files here by hand.
Course PDFs and readings are not published.
