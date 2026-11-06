---
title: InContext
emoji: 🗺️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
short_description: Spanish regional news next to official data
---

# InContext

For each Spanish autonomous community and sector: the latest news from several outlets, the
coverage of the same story grouped across outlets, the stories that led to it, and who governs,
next to official statistics.

- Code: https://github.com/JuanAntonioLeonOjeda/context-back (API and data pipeline) and
  https://github.com/JuanAntonioLeonOjeda/context-front (web app).
- **News:** only the headline, the date and a link to the outlet are shown.
- **Data:** a daily snapshot of the project's database; the news is at most a day old.
- Statistics from the INE and boundaries from the IGN (CC BY 4.0); each source is named next to
  its data in the web app.
