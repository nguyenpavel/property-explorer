/*
  METROPOLIS TOWER: unofficial demo data.

  Apartment data comes from Central Group's public price list
  (https://www.central-group.cz/prehled-bytu/217), read on 31 October 2026.
  It lists 100 available apartments on floors 1-8. Unit numbers in that range
  that aren't listed are marked "sold" (sold or reserved). Floors 9-22 haven't
  been released yet. Prices include VAT and will go out of date.

  The tower and floor-plate drawings were made for this demo. The plate is a
  schematic built from each unit's size and orientation, not the official plan.

  Each apartment sits in a `slot`: an outline on the floor-plate drawing, as
  four [x, y] corners in image fractions (add ?calibrate to the URL to read
  coordinates). Floors 1-2 split slot 8 into 8a and 8b.
*/
window.PROPERTY = {
  name: "Metropolis Tower",
  location: "Praha 10 · Malešice · unofficial demo",
  mark: "M",
  logo: null,

  mediaSize: [1920, 1080],
  locale: "cs-CZ",
  currency: "CZK",

  nav: [],
  cta: { label: "Official site", href: "https://www.central-group.cz/lokalita/217" },
  source: {
    label: "Official price list",
    href: "https://www.central-group.cz/prehled-bytu/217",
    note: "Data from Central Group's public price list, read 31 Oct 2026. Prices include VAT and change often.",
  },
  // Each listed apartment links to its own page (floor plan, rooms) on the developer's site.
  aptLink: {
    label: "Official floor plan",
    href: apt => `https://www.central-group.cz/byt-detail/217-01-${apt.unit.replace(/\D/g, "").padStart(3, "0")}`,
  },

  legal: "Unofficial concept demo, not affiliated with Central Group. Illustrations are schematic, not the official design.",

  statusLabels: { sold: "Sold or reserved", upcoming: "Next sales phase" },
  aptNote: "Heat-recovery ventilation and exterior blinds are included in every listed apartment.",
  soldNote: "This apartment isn't in the public price list, so it has been sold or reserved.",

  tower: {
    image: "media/tower.svg",
    focus: [0.5, 0.5],
    outline: {
      topLeft: [0.3958, 0.1944],
      topRight: [0.6042, 0.1944],
      bottomRight: [0.6042, 0.8056],
      bottomLeft: [0.3958, 0.8056],
    },
    floors: [1, 22],
  },

  plates: {
    standard: {
      image: "media/plate.svg",
      frame: [0.193, 0.185, 0.807, 0.8],
      slots: {
        0: [[0.4986, 0.5370], [0.6068, 0.5370], [0.6068, 0.7222], [0.4986, 0.7222]],
        1: [[0.4107, 0.5370], [0.4986, 0.5370], [0.4986, 0.7222], [0.4107, 0.7222]],
        2: [[0.3229, 0.5370], [0.4107, 0.5370], [0.4107, 0.7222], [0.3229, 0.7222]],
        3: [[0.2188, 0.4722], [0.3229, 0.4722], [0.3229, 0.7222], [0.2188, 0.7222]],
        4: [[0.2188, 0.2778], [0.3229, 0.2778], [0.3229, 0.4722], [0.2188, 0.4722]],
        5: [[0.3229, 0.2778], [0.3825, 0.2778], [0.3825, 0.4630], [0.3229, 0.4630]],
        6: [[0.3825, 0.2778], [0.4422, 0.2778], [0.4422, 0.4630], [0.3825, 0.4630]],
        7: [[0.4422, 0.2778], [0.4947, 0.2778], [0.4947, 0.4630], [0.4422, 0.4630]],
        8: [[0.4947, 0.2778], [0.6025, 0.2778], [0.6025, 0.4630], [0.4947, 0.4630]],
        "8a": [[0.4947, 0.2778], [0.5486, 0.2778], [0.5486, 0.4630], [0.4947, 0.4630]],
        "8b": [[0.5486, 0.2778], [0.6025, 0.2778], [0.6025, 0.4630], [0.5486, 0.4630]],
        9: [[0.6025, 0.2778], [0.6875, 0.2778], [0.6875, 0.4630], [0.6025, 0.4630]],
        10: [[0.6875, 0.2778], [0.7812, 0.2778], [0.7812, 0.4398], [0.6875, 0.4398]],
        11: [[0.6875, 0.4398], [0.7812, 0.4398], [0.7812, 0.5694], [0.6875, 0.5694]],
        12: [[0.6875, 0.5694], [0.7812, 0.5694], [0.7812, 0.7222], [0.6875, 0.7222]],
        13: [[0.6068, 0.5370], [0.6875, 0.5370], [0.6875, 0.7222], [0.6068, 0.7222]],
      },
    },
  },

  floors: [
    { floors: [1, 8], plate: "standard" },
    { floors: [9, 22], status: "upcoming", note: "Layouts and prices not published yet" },
  ],

  apartments: [
    { unit: "A 1", floor: 1, slot: 0, status: "sold" },
    { unit: "A 2", floor: 1, slot: 1, layout: "2+kk", area: 53.9, outdoor: 4.4, facing: "West", price: 7864799 },
    { unit: "A 3", floor: 1, slot: 2, layout: "2+kk", area: 54, outdoor: 8.2, facing: "West", price: 8147935 },
    { unit: "A 4", floor: 1, slot: 3, layout: "3+kk", area: 80, outdoor: 17.4, facing: "North-west", price: 10930425 },
    { unit: "A 5", floor: 1, slot: 4, layout: "2+kk", area: 52.5, outdoor: 11.1, facing: "North-east", price: 7773832 },
    { unit: "A 6", floor: 1, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6184575 },
    { unit: "A 7", floor: 1, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6184575 },
    { unit: "A 8", floor: 1, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.8, facing: "East", price: 5822367 },
    { unit: "A 9", floor: 1, slot: "8a", layout: "1+kk", area: 29.8, outdoor: 4.6, facing: "East", price: 5833903 },
    { unit: "A 10", floor: 1, slot: "8b", layout: "1+kk", area: 29, outdoor: 0, facing: "East", price: 5709084 },
    { unit: "A 11", floor: 1, slot: 9, layout: "2+kk", area: 48.1, outdoor: 9.7, facing: "East", price: 7432031 },
    { unit: "A 12", floor: 1, slot: 10, layout: "3+kk", area: 79, outdoor: 11.4, facing: "South-east", price: 10579976 },
    { unit: "A 13", floor: 1, slot: 11, layout: "2+kk", area: 51.2, outdoor: 7, facing: "South", price: 7501023 },
    { unit: "A 14", floor: 1, slot: 12, layout: "3+kk", area: 75.5, outdoor: 22.4, facing: "South-west", price: 10566153 },
    { unit: "A 15", floor: 1, slot: 13, layout: "2+kk", area: 49.7, outdoor: 4, facing: "West", price: 7454655 },

    { unit: "A 16", floor: 2, slot: 0, layout: "2+kk", area: 66.4, outdoor: 4.9, facing: "West", price: 8465934 },
    { unit: "A 17", floor: 2, slot: 1, status: "sold" },
    { unit: "A 18", floor: 2, slot: 2, layout: "2+kk", area: 53.7, outdoor: 4.6, facing: "West", price: 8061536 },
    { unit: "A 19", floor: 2, slot: 3, layout: "3+kk", area: 79.7, outdoor: 16, facing: "North-west", price: 10917514 },
    { unit: "A 20", floor: 2, slot: 4, status: "sold" },
    { unit: "A 21", floor: 2, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.7, facing: "East", price: 6223952 },
    { unit: "A 22", floor: 2, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6228432 },
    { unit: "A 23", floor: 2, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.4, facing: "East", price: 5839792 },
    { unit: "A 24", floor: 2, slot: "8a", layout: "1+kk", area: 29.4, outdoor: 0, facing: "East", price: 5789437 },
    { unit: "A 25", floor: 2, slot: "8b", layout: "1+kk", area: 29.4, outdoor: 4.6, facing: "East", price: 5795888 },
    { unit: "A 26", floor: 2, slot: 9, layout: "2+kk", area: 47.7, outdoor: 5.4, facing: "East", price: 7492688 },
    { unit: "A 27", floor: 2, slot: 10, layout: "3+kk", area: 79.5, outdoor: 18.7, facing: "South-east", price: 10641670 },
    { unit: "A 28", floor: 2, slot: 11, status: "sold" },
    { unit: "A 29", floor: 2, slot: 12, layout: "3+kk", area: 75.3, outdoor: 22.1, facing: "South-west", price: 10603382 },
    { unit: "A 30", floor: 2, slot: 13, layout: "2+kk", area: 49.7, outdoor: 4, facing: "West", price: 7479024 },

    { unit: "A 31", floor: 3, slot: 0, layout: "2+kk", area: 66.5, outdoor: 4.9, facing: "West", price: 8547134 },
    { unit: "A 32", floor: 3, slot: 1, layout: "2+kk", area: 54.1, outdoor: 4.4, facing: "West", price: 7949872 },
    { unit: "A 33", floor: 3, slot: 2, layout: "2+kk", area: 53.7, outdoor: 4, facing: "West", price: 8090320 },
    { unit: "A 34", floor: 3, slot: 3, layout: "3+kk", area: 80.1, outdoor: 17.1, facing: "North-west", price: 11120005 },
    { unit: "A 35", floor: 3, slot: 4, status: "sold" },
    { unit: "A 36", floor: 3, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.2, facing: "East", price: 6236272 },
    { unit: "A 37", floor: 3, slot: 6, layout: "1+kk", area: 33.4, outdoor: 0, facing: "East", price: 6139549 },
    { unit: "A 38", floor: 3, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.8, facing: "East", price: 5888176 },
    { unit: "A 39", floor: 3, slot: 8, status: "sold" },
    { unit: "A 40", floor: 3, slot: 9, status: "sold" },
    { unit: "A 41", floor: 3, slot: 10, layout: "3+kk", area: 79, outdoor: 11.1, facing: "South-east", price: 10639654 },
    { unit: "A 42", floor: 3, slot: 11, status: "sold" },
    { unit: "A 43", floor: 3, slot: 12, layout: "3+kk", area: 75.1, outdoor: 17.9, facing: "South-west", price: 10590121 },
    { unit: "A 44", floor: 3, slot: 13, layout: "2+kk", area: 50.2, outdoor: 9.5, facing: "West", price: 7749504 },

    { unit: "A 45", floor: 4, slot: 0, layout: "2+kk", area: 66.8, outdoor: 4.9, facing: "West", price: 8593984 },
    { unit: "A 46", floor: 4, slot: 1, layout: "2+kk", area: 54.5, outdoor: 8.2, facing: "West", price: 8139936 },
    { unit: "A 47", floor: 4, slot: 2, layout: "2+kk", area: 53.7, outdoor: 4.6, facing: "West", price: 8166032 },
    { unit: "A 48", floor: 4, slot: 3, layout: "3+kk", area: 79.3, outdoor: 12.7, facing: "North-west", price: 10807786 },
    { unit: "A 49", floor: 4, slot: 4, status: "sold" },
    { unit: "A 50", floor: 4, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.7, facing: "East", price: 6356000 },
    { unit: "A 51", floor: 4, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6360480 },
    { unit: "A 52", floor: 4, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.4, facing: "East", price: 5954816 },
    { unit: "A 53", floor: 4, slot: 8, status: "sold" },
    { unit: "A 54", floor: 4, slot: 9, layout: "2+kk", area: 47.8, outdoor: 5.4, facing: "East", price: 7502208 },
    { unit: "A 55", floor: 4, slot: 10, layout: "3+kk", area: 79.5, outdoor: 18.7, facing: "South-east", price: 10899972 },
    { unit: "A 56", floor: 4, slot: 11, status: "sold" },
    { unit: "A 57", floor: 4, slot: 12, status: "sold" },
    { unit: "A 58", floor: 4, slot: 13, status: "sold" },

    { unit: "A 59", floor: 5, slot: 0, layout: "2+kk", area: 66.8, outdoor: 4.9, facing: "West", price: 8661520 },
    { unit: "A 60", floor: 5, slot: 1, layout: "2+kk", area: 54.1, outdoor: 4.4, facing: "West", price: 8164352 },
    { unit: "A 61", floor: 5, slot: 2, layout: "2+kk", area: 53.7, outdoor: 4, facing: "West", price: 8194816 },
    { unit: "A 62", floor: 5, slot: 3, layout: "3+kk", area: 80.1, outdoor: 17.1, facing: "North-west", price: 11176306 },
    { unit: "A 63", floor: 5, slot: 4, layout: "2+kk", area: 52.5, outdoor: 11.1, facing: "North-east", price: 8110905 },
    { unit: "A 64", floor: 5, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6395200 },
    { unit: "A 65", floor: 5, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6395200 },
    { unit: "A 66", floor: 5, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.8, facing: "East", price: 6003200 },
    { unit: "A 67", floor: 5, slot: 8, status: "sold" },
    { unit: "A 68", floor: 5, slot: 9, layout: "2+kk", area: 47.8, outdoor: 5, facing: "East", price: 7534016 },
    { unit: "A 69", floor: 5, slot: 10, layout: "3+kk", area: 79.5, outdoor: 18.7, facing: "South-east", price: 10981284 },
    { unit: "A 70", floor: 5, slot: 11, layout: "2+kk", area: 50.9, outdoor: 3.7, facing: "South", price: 7665280 },
    { unit: "A 71", floor: 5, slot: 12, layout: "3+kk", area: 75.1, outdoor: 17.9, facing: "South-west", price: 10501437 },
    { unit: "A 72", floor: 5, slot: 13, layout: "2+kk", area: 50.2, outdoor: 9.5, facing: "West", price: 7828800 },

    { unit: "A 73", floor: 6, slot: 0, layout: "2+kk", area: 67.3, outdoor: 9.5, facing: "West", price: 8885184 },
    { unit: "A 74", floor: 6, slot: 1, layout: "2+kk", area: 54.1, outdoor: 3.6, facing: "West", price: 8183840 },
    { unit: "A 75", floor: 6, slot: 2, layout: "2+kk", area: 54.1, outdoor: 8.2, facing: "West", price: 8411760 },
    { unit: "A 76", floor: 6, slot: 3, layout: "3+kk", area: 79.8, outdoor: 12.8, facing: "North-west", price: 11085265 },
    { unit: "A 77", floor: 6, slot: 4, layout: "2+kk", area: 53, outdoor: 13.4, facing: "North-east", price: 8311909 },
    { unit: "A 78", floor: 6, slot: 5, layout: "1+kk", area: 33.4, outdoor: 0, facing: "East", price: 6306048 },
    { unit: "A 79", floor: 6, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4, facing: "East", price: 6394080 },
    { unit: "A 80", floor: 6, slot: 7, layout: "1+kk", area: 29.4, outdoor: 0, facing: "East", price: 5883136 },
    { unit: "A 81", floor: 6, slot: 8, layout: "2+kk", area: 61.1, outdoor: 4, facing: "East", price: 8251264 },
    { unit: "A 82", floor: 6, slot: 9, layout: "2+kk", area: 47.7, outdoor: 4.4, facing: "East", price: 7540288 },
    { unit: "A 83", floor: 6, slot: 10, layout: "3+kk", area: 79.5, outdoor: 17.4, facing: "South-east", price: 11033252 },
    { unit: "A 84", floor: 6, slot: 11, layout: "2+kk", area: 50.8, outdoor: 3.3, facing: "South", price: 7683200 },
    { unit: "A 85", floor: 6, slot: 12, layout: "3+kk", area: 75.5, outdoor: 22.4, facing: "South-west", price: 10787485 },
    { unit: "A 86", floor: 6, slot: 13, layout: "2+kk", area: 49.7, outdoor: 4.3, facing: "West", price: 7685440 },

    { unit: "A 87", floor: 7, slot: 0, layout: "2+kk", area: 66.7, outdoor: 4.4, facing: "West", price: 8745744 },
    { unit: "A 88", floor: 7, slot: 1, layout: "2+kk", area: 54.1, outdoor: 4, facing: "West", price: 8257088 },
    { unit: "A 89", floor: 7, slot: 2, layout: "2+kk", area: 54.1, outdoor: 8.2, facing: "West", price: 8467872 },
    { unit: "A 90", floor: 7, slot: 3, layout: "3+kk", area: 80.1, outdoor: 17.4, facing: "North-west", price: 11353042 },
    { unit: "A 91", floor: 7, slot: 4, layout: "2+kk", area: 52.5, outdoor: 11.1, facing: "North-east", price: 8220665 },
    { unit: "A 92", floor: 7, slot: 5, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6464640 },
    { unit: "A 93", floor: 7, slot: 6, layout: "1+kk", area: 33.8, outdoor: 4.8, facing: "East", price: 6464640 },
    { unit: "A 94", floor: 7, slot: 7, layout: "1+kk", area: 29.8, outdoor: 4.8, facing: "East", price: 6064128 },
    { unit: "A 95", floor: 7, slot: 8, layout: "2+kk", area: 61.1, outdoor: 4.6, facing: "East", price: 8339296 },
    { unit: "A 96", floor: 7, slot: 9, layout: "2+kk", area: 48.2, outdoor: 9.7, facing: "East", price: 7802144 },
    { unit: "A 97", floor: 7, slot: 10, layout: "3+kk", area: 79, outdoor: 11.4, facing: "South-east", price: 10840836 },
    { unit: "A 98", floor: 7, slot: 11, layout: "2+kk", area: 51.3, outdoor: 7, facing: "South", price: 7904288 },
    { unit: "A 99", floor: 7, slot: 12, layout: "3+kk", area: 75.5, outdoor: 22.4, facing: "South-west", price: 10864989 },
    { unit: "A 100", floor: 7, slot: 13, layout: "2+kk", area: 49.7, outdoor: 4.3, facing: "West", price: 7735392 },

    { unit: "A 101", floor: 8, slot: 0, layout: "2+kk", area: 67.3, outdoor: 4.9, facing: "West", price: 9042880 },
    { unit: "A 102", floor: 8, slot: 1, layout: "2+kk", area: 54.7, outdoor: 8.2, facing: "West", price: 8619520 },
    { unit: "A 103", floor: 8, slot: 2, layout: "2+kk", area: 54.1, outdoor: 4.6, facing: "West", price: 8583456 },
    { unit: "A 104", floor: 8, slot: 3, layout: "3+kk", area: 80, outdoor: 12.7, facing: "North-west", price: 11419082 },
    { unit: "A 105", floor: 8, slot: 4, layout: "2+kk", area: 53.4, outdoor: 9.7, facing: "North-east", price: 8470350 },
    { unit: "A 106", floor: 8, slot: 5, layout: "1+kk", area: 34.1, outdoor: 4.7, facing: "East", price: 6515152 },
    { unit: "A 107", floor: 8, slot: 6, layout: "1+kk", area: 34.1, outdoor: 4.8, facing: "East", price: 6519632 },
    { unit: "A 108", floor: 8, slot: 7, layout: "1+kk", area: 30.2, outdoor: 4.4, facing: "East", price: 6141520 },
    { unit: "A 109", floor: 8, slot: 8, layout: "2+kk", area: 61.6, outdoor: 4.6, facing: "East", price: 8445472 },
    { unit: "A 110", floor: 8, slot: 9, layout: "2+kk", area: 48.2, outdoor: 5.4, facing: "East", price: 7785120 },
    { unit: "A 111", floor: 8, slot: 10, layout: "3+kk", area: 80.1, outdoor: 18.7, facing: "South-east", price: 11298020 },
    { unit: "A 112", floor: 8, slot: 11, layout: "2+kk", area: 51.2, outdoor: 3.7, facing: "South", price: 7992432 },
    { unit: "A 113", floor: 8, slot: 12, layout: "3+kk", area: 75.7, outdoor: 22.1, facing: "South-west", price: 11176797 },
    { unit: "A 114", floor: 8, slot: 13, layout: "2+kk", area: 50.3, outdoor: 4, facing: "West", price: 7992544 },
  ],
};
