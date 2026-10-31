/*
  PROPERTY DATA — this is the only file you need to edit.

  Everything below is SAMPLE content wired to the placeholder art in /media.
  Replace names, numbers, copy and image paths with the real property.

  Positions are fractions of the image: [x, y] where [0, 0] is the top-left
  corner and [1, 1] is the bottom-right. Add ?calibrate to the URL
  (e.g. http://localhost:8000/?calibrate) to see the coordinates under your
  cursor and the floor outlines drawn on the tower.

  Every scene image should be the same size (default 1920x1080). Transition
  clips are optional: leave `clip: null` and the site uses a zoom effect.
  See README.md for how to make clips that line up with the stills.
*/
window.PROPERTY = {
  name: "Property Name",
  location: "Neighborhood · City",
  mark: "P",          // letter shown in the logo square
  logo: null,         // or a path like "media/brand/logo.svg" to use an image instead

  mediaSize: [1920, 1080],  // pixel size of the scene images

  nav: [
    { label: "Residences", href: "#/floor/12" },
    { label: "Penthouses", href: "#/floor/29" },
  ],
  cta: { label: "Private Tour" },

  legal: "Renderings are artist's conceptions and subject to change. Sample content.",

  // Where tour / floor plan requests go. Set ONE of these:
  //   endpoint: a form service URL that accepts POST (e.g. https://formspree.io/f/xxxxxxx)
  //   email:    opens the visitor's email app addressed to this inbox
  leads: {
    endpoint: "",
    email: "",
  },

  tower: {
    image: "media/tower/tower.svg",
    focus: [0.5, 0.5],  // point kept on screen when the image is cropped (phones)
    // The four corners of the stack of floors you want clickable, in image fractions.
    outline: {
      topLeft: [0.4375, 0.1481],
      topRight: [0.5625, 0.1481],
      bottomRight: [0.5625, 0.7315],
      bottomLeft: [0.4375, 0.7315],
    },
    floors: [3, 30],  // [floor at the bottom edge of the outline, floor at the top edge]
  },

  residences: {
    "residence-a": {
      name: "Residence A",
      beds: 2,
      baths: 2,
      sqft: 1450,
      priceFrom: 1560000,
      description:
        "A bay-facing two-bedroom with a full wall of glass, an open chef's kitchen and a primary suite with a spa bath and walk-in closet.",
      plan: {
        image: "media/residence-a/plan.svg",
        // Box around the floor plan drawing [left, top, right, bottom]. Keeps it visible next to the side panel.
        frame: [0.07, 0.11, 0.727, 0.899],
      },
      towerClip: null,      // e.g. "media/clips/tower-to-residence-a.mp4"
      towerBackClip: null,  // optional reverse clip, plan -> tower
      rooms: [
        { id: "living", name: "Living & Kitchen", hotspot: [0.364, 0.514], image: "media/residence-a/living.svg", clip: null },
        { id: "primary-bedroom", name: "Primary Bedroom", hotspot: [0.613, 0.536], image: "media/residence-a/primary-bedroom.svg", clip: null },
        { id: "primary-bath", name: "Primary Bath", hotspot: [0.553, 0.747], image: "media/residence-a/primary-bath.svg", clip: null },
      ],
    },

    penthouse: {
      name: "Sky Penthouse",
      beds: 3,
      baths: 3.5,
      sqft: 3200,
      priceFrom: 7200000,
      description:
        "A full corner of sky. Glass on two sides, a wraparound terrace, a chef's kitchen in dark stone and a primary suite with a soaking tub.",
      plan: {
        image: "media/penthouse/plan.svg",
        frame: [0.108, 0.11, 0.689, 0.899],
      },
      towerClip: null,
      towerBackClip: null,
      rooms: [
        { id: "great-room", name: "Great Room", hotspot: [0.389, 0.394], image: "media/penthouse/great-room.svg", clip: null },
        { id: "kitchen", name: "Chef's Kitchen", hotspot: [0.555, 0.525], image: "media/penthouse/kitchen.svg", clip: null },
        { id: "primary-suite", name: "Primary Suite", hotspot: [0.501, 0.693], image: "media/penthouse/primary-suite.svg", clip: null },
        { id: "spa-bath", name: "Spa Bath", hotspot: [0.27, 0.275], image: "media/penthouse/spa-bath.svg", clip: null },
      ],
    },
  },

  // Which residence is on which floor. Later entries override earlier ones,
  // so list the ranges first and individual exceptions after.
  // status: "available" | "reserved" | "sold"   (price is hidden when sold)
  // Optional per-floor fields: priceFrom, towerClip
  floors: [
    { floors: [3, 27], residence: "residence-a", status: "available" },
    { floors: [28, 30], residence: "penthouse", status: "available" },
    { floors: [16, 27], priceFrom: 1690000 },
    { floor: 8, status: "sold" },
    { floor: 14, status: "reserved" },
    { floor: 21, status: "sold" },
    { floor: 30, status: "sold" },
  ],
};
