QUAD - HOW THE DATA STAYS UP TO DATE
====================================

WHAT'S IN THIS FOLDER
- index.html: the app
- quad-data.json: the data file the app reads. It's updated automatically.
- tools/collect-halls.mjs: the halls price checker. It visits every uni's
  website, finds the accommodation price pages and reads the weekly price
  for each room type.
- tools/build-data.mjs: copies the checked prices into quad-data.json.
- tools/unis.json: the list of uni websites. If the checker can't find a
  uni's prices, paste that uni's price page link into its "start": [] list.
- .github/workflows/update-data.yml: runs the checker on GitHub on the 1st
  of every month. (This is a hidden folder. In Finder, press Cmd+Shift+.
  to see it.)

HOW CONFIDENT THE CHECKER IS
- high: 6 or more prices plus a year like 2026/27 found. Used automatically.
- medium: 3 to 5 prices found. Used, and marked with a yellow dot.
- low or none: not used. The uni is listed in data/halls-review.md so you
  can check it by hand. This happens when a site blocks robots or loads its
  prices with JavaScript.

CHECKED BY HAND (24 Oct 2026)
- Paramedic Science courses and apprenticeships: HCPC register
- Tuition fee cap in England: GBP 9,790 (2026/27), GBP 10,050 (2027/28)

STILL ESTIMATES
- Courses for other subjects, satisfaction, offers and graduate data.
  Replace these with the Discover Uni dataset.

OPTIONAL
- Set REPORT_EMAIL in index.html so "Report a mistake" messages come to you.
