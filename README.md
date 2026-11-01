# Property Explorer

An interactive residence explorer for a tower. Visitors hover over a floor on the building, click into an isometric floor plan, then into photoreal renders of each room. Transitions use pre-rendered video clips when you provide them and a zoom effect when you don't.

It's a static site (plain HTML, CSS and JavaScript, no build step), hosted on GitHub Pages.

**Everything currently in the site is placeholder content.** The images in `media/` are labeled placeholders, and the names, prices and copy in `data/property.js` are samples.

## Preview locally

```sh
python -m http.server 8000
# then open http://localhost:8000
```

Any static server works. Opening `index.html` straight from disk mostly works too, but clips won't preload that way.

## Where things live

```
data/property.js   ← all content: names, floors, prices, image paths, clips
media/             ← images and clips (replace the placeholders here)
index.html
css/styles.css
js/app.js
```

You should only need to edit `data/property.js` and add files to `media/`.

## Adding the real property

### 1. Images

All scene images should be the same size and aspect ratio. The default is 1920×1080 (set `mediaSize` if yours differ). Use JPG or WebP for renders, and keep each under about 600 KB.

| Scene | What it is | Notes |
| --- | --- | --- |
| Tower | The building, ideally straight-on | The floors need to be visible and roughly level |
| Floor plan | Isometric cutaway of one residence type, on a plain dark background | Leave the right ~30% fairly empty; the info panel sits there |
| Rooms | One render per room | Keep the bottom ~25% calm; captions and tabs sit there |

Drop the files into `media/` and update the paths in `data/property.js`.

### 2. Line up the floors and hotspots

Add `?calibrate` to the URL (e.g. `http://localhost:8000/?calibrate`). The site then draws every clickable floor on the tower and shows the coordinates under your cursor. Press **C** to copy them.

- **Tower:** set `tower.outline` to the four corners of the stack of floors you want clickable, and `tower.floors` to `[bottom floor, top floor]` within that outline. Floors are spaced evenly between the corners. That's accurate for a straight-on photo and approximate for one with strong perspective.
- **Floor plans:** set each room's `hotspot` to where its dot should sit. Set `plan.frame` to the box around the drawing (`[left, top, right, bottom]`), so the plan stays visible beside the panel and on phones.

### 3. Floors, prices and availability

The `floors` list maps floor numbers to residence types. Later entries override earlier ones, so list ranges first and exceptions after:

```js
floors: [
  { floors: [3, 27], residence: "residence-a", status: "available" },
  { floors: [16, 27], priceFrom: 1690000 },   // higher floors cost more
  { floor: 21, status: "sold" },
]
```

`status` can be `available`, `reserved` or `sold`. Sold units hide their price.

## Transition clips (Seedance or similar)

Clips are optional. A clip plays on top of the current still, and the next still takes over on its last frame. So each clip must start and end on exactly the images the site shows.

Use first-frame / last-frame (image-to-video) generation:

| Clip | First frame | Last frame | Config field |
| --- | --- | --- | --- |
| Tower → plan | `tower` image | that residence's `plan` image | `residences.<id>.towerClip` |
| Plan → room | the `plan` image | that room's `image` | `rooms[].clip` |
| Plan → tower (optional) | `plan` | `tower` | `residences.<id>.towerBackClip` |
| Room → plan (optional) | room `image` | `plan` | `rooms[].backClip` |

Without a back clip, going back uses the zoom effect, which looks fine.

The tower clip is per residence type, so it zooms into one representative floor. If you want a specific floor to have its own clip, add `towerClip` to that floor's entry in `floors`.

Prompt ideas: *"slow cinematic camera push into the 20th floor of the tower, the facade opens to reveal an isometric cutaway of the apartment"* and *"camera glides down into the living room of the cutaway model and settles at eye level"*.

Export as MP4 (H.264), at the same aspect ratio as the stills, 3–5 seconds, with no audio. Keep each clip under about 5 MB. With ffmpeg:

```sh
ffmpeg -i raw.mp4 -vf scale=1920:-2 -c:v libx264 -crf 23 -preset slow -an -movflags +faststart media/clips/tower-to-residence-a.mp4
```

Clips download in the background when someone hovers a floor or room, so they usually start instantly. If a clip is missing or fails to load, the site falls back to the zoom. Visitors with reduced motion enabled get a simple crossfade.

## Buildings sold apartment by apartment

For a building with many apartments per floor, give floors a `plate` instead of a `residence`. The visitor goes tower → floor plate (apartments coloured by status) → apartment details. [metropolis/](metropolis/) is a full example built from a real price list.

- `plates.<id>`: the floor-plate `image`, its `frame`, and `slots`, the outline of each apartment position as `[x, y]` corners.
- `apartments`: one entry per apartment with `unit`, `floor`, `slot`, and optionally `layout`, `area`, `outdoor`, `facing`, `price` and `status`.
- A floor entry with only a `status` (and an optional `note`) shows a card but can't be opened, which suits floors not yet on sale.
- `locale` and `currency` (e.g. `"cs-CZ"`, `"CZK"`) format prices; `statusLabels` renames statuses.
- `cta.href` turns the top-right button into a link, and `source` adds a link and a data note under each panel.
- `aptLink` (a label and a function from apartment to URL) links each available apartment to its own page elsewhere, such as the developer's listing.

Each page is a copy of `index.html` with its own data file, sharing `css/` and `js/`.

## Tour and floor plan requests

The "Private Tour" and "Request floor plan" buttons open a short form. Connect it in `data/property.js`:

- `leads.endpoint`: a form service URL that accepts POST, such as [Formspree](https://formspree.io). Submissions arrive in your inbox.
- or `leads.email`: opens the visitor's email app with the request filled in.

Until one is set, the form tells visitors it isn't connected.

## Publishing

The site deploys to GitHub Pages from the `main` branch. Every push to `main` goes live within a minute or two.
