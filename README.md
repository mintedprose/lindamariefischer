# lindamariefischer.com

Linda Marie Fischer's music site. It's built with Jekyll and hosted free on GitHub Pages. Design notes for developers are in [NOTES-FOR-AMEBA.md](NOTES-FOR-AMEBA.md).

## Common updates

**Add a blog post:** copy any file in `_posts/`, rename it `YYYY-MM-DD-short-title.html`, and change the top section:

```
---
layout: "post"
title: "Your title"
date: "2026-10-15 10:00:00"
permalink: "/blog/short-title"
image: "/assets/img/site/your-picture.jpg"
excerpt: "One or two sentences shown on the blog page."
tags: ["music"]
---
<p>Your post text…</p>
```

Put the picture in `assets/img/site/`. The Home page and the Blog page pick up the new post automatically.

**Change a Spotify / Apple / Amazon link:** edit `_data/albums.yml`. Every page uses that file.

**Change the menu or footer:** `_includes/header.html` and `_includes/footer.html`.

## Publishing

Commit and push to `main` in GitHub Desktop, and GitHub Pages rebuilds the site in about a minute.
