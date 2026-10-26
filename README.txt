QUAD - WHERE THE DATA COMES FROM AND HOW IT STAYS UP TO DATE
============================================================

OFFICIAL DATA (updated once a year)
Source: the Discover Uni dataset from HESA and the Office for Students,
licensed under CC BY 4.0. It covers:
- which unis run each course
- student satisfaction (NSS)
- entrants' grades
- how many students carry on after year 1
- graduate salary and jobs
- placement years, years abroad and accreditation
- TEF teaching ratings
- campus locations

How to update it each October:
1. Go to hesa.ac.uk, then Open data, then "Discover Uni dataset".
2. Download the CSV zip.
3. Either send it to Claude, or upload it to the source/ folder in the
   GitHub repository. GitHub imports it automatically.
A yearly reminder is set for 24 October.

HALLS PRICES (checked automatically every month)
- Each uni's own published fee pages are checked automatically on the
  1st of every month.
- tools/halls-manual.json holds the prices that were checked by hand. A
  newer automatic result replaces a hand-checked price.
- data/halls-review.md lists the unis that need checking by hand.

OTHER
- Tuition fees use the government fee cap.
- Degree apprenticeships only list programmes on the HCPC register, plus
  links to live vacancy sites.
- If a uni doesn't publish something, Quad says "No official data" or
  "Not published" rather than guessing.

FILES
- index.html: the app
- quad-data.js and quad-data.json: all the data. These are built
  automatically, so don't edit them by hand.
- tools/import-discover-uni.py: reads the Discover Uni zip
- tools/collect-halls.mjs: the monthly halls price checker
- tools/build-data.mjs: combines everything into quad-data.js and
  quad-data.json
- tools/uni-ids.json: each uni's official ID (UKPRN)
- tools/unis.json: the uni websites the halls price checker visits
