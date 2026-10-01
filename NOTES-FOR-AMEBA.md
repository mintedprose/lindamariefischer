# lindamariefischer.com: design handoff notes for Ameba

Hi Ameba team,

This is the new **Linda Marie Fischer** music site. It replaces the current Squarespace site at lindamariefischer.com. All the content has been moved over, and a first refreshed design is in place. We'd like you to take the design from "clean and working" to "polished." A PDF of every page is included (`LMF Website Proof.pdf`) so you can see where it stands today.

---

## 1. How the site is built

- **Jekyll on GitHub Pages.** Standard `github-pages` gem, no plugins, no custom build. GitHub builds it on every push to `main`.
- **Plain HTML + one CSS file + one small JS file.** No frameworks and no npm.
- **Local preview:** `bundle install` then `bundle exec jekyll serve`, and open http://localhost:4000.

```
_config.yml          site settings (title, url, baseurl)
_data/albums.yml     the 3 albums: titles, covers, and Spotify / Apple / Amazon links (one place for every link)
_includes/           head.html, header.html (menu), footer.html, social.html, listen.html (streaming buttons)
_layouts/            default.html (page shell), page.html, album.html, post.html, redirect.html
_posts/              41 blog posts, one HTML file each (front matter + body)
index.html           home page
*.html (root)        content pages: story, videos, lyrics, songwriter notes, media, merch, faq, …
blog/index.html      blog listing (loops over site.posts)
redirects/           stubs that keep old Squarespace URLs working (/albums, /lyrics, /home, …)
assets/css/site.css  ALL styles; colour and font tokens at the top in :root
assets/js/site.js    mobile menu, dropdowns, click-to-play YouTube
assets/img/          design images; assets/img/site/ = images carried over from the old site
assets/files/        lyric-sheet PDFs
_build/              one-off migration scripts (ignore; see section 6)
```

**Where to work:** almost everything is in `assets/css/site.css`, `_layouts/` and `_includes/`. The page files hold Linda's words, and those should stay as they are (see the ground rules below).

When you change the CSS or JS, **bump the `?v=` number** in `_includes/head.html` (CSS) or `_layouts/default.html` (JS) so browsers pick up the new file.

---

## 2. What we'd love from you

The structure, content and URLs are settled. The scope is **visual polish**:

1. **Type and spacing system.** Refine the heading scale, line lengths and vertical rhythm across page types. Today it's Cormorant Garamond (headings) with Jost (body).
2. **Home page.** The hero is edge-to-edge on purpose (the photo fills the right half with no frame), and Linda chose this over an arch and a framed version. Refine it, but please keep that approach. The "Roots Flourish" section uses the watercolor bouquet on purpose. Linda doesn't want a second photo there.
3. **Album pages** (`_layouts/album.html`) and the Album / Lyrics / Songwriter Notes tabs.
4. **Songwriter Notes pages.** These are long, two-voice pages ("Linda's Take" / "Phil's View"). Help them read beautifully on desktop and phone.
5. **Videos page** (12 videos) and **Inspiration gallery**.
6. **Blog listing and post template.**
7. **Mobile menu and dropdowns.** They work, but they're basic.
8. **Performance and accessibility pass.** Responsive `srcset`/WebP for the big images in `assets/img/site/`, colour contrast, focus states, alt text where it's missing.
9. **Social share image.** Right now `og:image` is the portrait for every page.

Anything else you'd suggest, please list it and we'll decide.

---

## 3. Ground rules

- **Don't change Linda's wording.** All page and blog text was carried over word for word from the old site. If you spot a typo or something that reads oddly (the FAQ heading "For Jnquiring Minds" is one), **flag it to Linda and don't edit it yourself**.
- **Keep every URL (permalink) as it is.** They match the old Squarespace addresses so search rankings and old links keep working. Don't rename page files' `permalink:` values or delete anything in `redirects/`.
- **Streaming links live only in `_data/albums.yml`.** Please don't hard-code them in templates.
- **Photos.** The hero portrait (`assets/img/portrait.jpg`, the white shirt against the sky) is the one Linda wants. **Don't use the 2019 studio headshots** (blue scarf, black dress, studio backdrop). Don't add photos of anyone outside Linda's own circle.
- **Colours** (Linda's choice): one cool family, with the logo teal `#00a6c8`, deep teal `#00627a` for solid buttons and accents, and **pale sky blue** backgrounds (`#eef5f9` → `#e3eff6`) taken from the sky in the hero photo. **Please don't reintroduce the dark green.** Linda found it heavy. Also on-brand: the watercolor wreath and bouquet art (2018 LMF style guide). The brand script/display fonts (Hymned Script, Hymned Sans, Majesti Banner) are only used inside the logo image. If you want them as web fonts, check that the licence allows web use first. Linda can send the style guide PDF and font files.
- **No newsletter signup for now** (the old one was broken). **No shop.** Merch links out to Redbubble.

---

## 4. How we'll work together

1. Linda adds you as a collaborator on the GitHub repo.
2. Work on a **branch** and open a **pull request**. Screenshots in the PR description are very welcome.
3. Linda reviews and merges. GitHub Pages then publishes automatically.

While the domain still points at Squarespace, the site is previewed at `https://<account>.github.io/<repo>/`. For that, `_config.yml` has `baseurl: "/<repo>"`, and all internal links go through `{{ site.baseurl }}`, so please keep using that in any new links.

---

## 5. Known items (already handled or waiting on Linda)

- **YouTube videos** use a thumbnail with a play button, and the player loads on click (`site.js`). This is faster and privacy-friendlier (youtube-nocookie).
- **Old press releases** (inside some blog posts) include "embed code" text with raw `<iframe>` markup shown as text. This is carried over exactly as it was on the old site.
- **Some blog links go through Mailchimp tracking URLs** (`list-manage.com`), carried over as they were.
- **Merch prices** in the captions come from the old site and may not match Redbubble today. That's Linda's call.
- **`music.lindamariefischer.com` is Linda's Bandcamp store** (a DNS CNAME to `dom.bandcamp.com`). It must keep working when the main domain moves.

---

## 6. The `_build/` folder

These are the scripts used to migrate the content out of Squarespace (`convert_pages.py`, `convert_blog.py`) and to make previews and the PDF proof on a machine without Ruby (`preview.py`, `shoot.py`, `make_pdf.py`). Jekyll ignores the folder, and you don't need any of it. Please don't re-run the converters, because they would overwrite edits.

Thank you!
