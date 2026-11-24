/** The drawing set shown after the walkthrough. Figures are taken from the model. */

export type Sheet = {
  code: string;
  title: string;
  scale: string;
  body: string[];
  facts: { term: string; value: string }[];
  drawing: "site" | "axonometric" | "plan" | "section" | "materials" | "environment";
};

export const SHEETS: Sheet[] = [
  {
    code: "A-101",
    title: "Site analysis",
    scale: "1:2500",
    drawing: "site",
    body: [
      "The plot runs 184 metres along the north shore. The house takes the one level shelf, thirteen metres back from the water, where the forest opens towards the lake.",
      "Behind it the ground climbs through larch and spruce to the Serein range. Evening light arrives from the west across the water.",
    ],
    facts: [
      { term: "Plot", value: "2.6 ha" },
      { term: "Shoreline", value: "184 m" },
      { term: "Elevation", value: "1,268 m" },
      { term: "Water at the dock", value: "3.1 m deep" },
    ],
  },
  {
    code: "A-102",
    title: "Guiding idea",
    scale: "Not to scale",
    drawing: "axonometric",
    body: [
      "Three volumes on a limestone plinth, each with one purpose: a glass gable for gathering, a stone core for arriving, a timber bar for sleeping.",
      "The plinth ties them to the shore and becomes the terrace, the pool edge and the steps down to the dock.",
    ],
    facts: [
      { term: "Gross floor area", value: "760 m²" },
      { term: "Footprint", value: "448 m²" },
      { term: "Bedrooms", value: "5" },
    ],
  },
  {
    code: "A-201",
    title: "Ground floor plan",
    scale: "1:200",
    drawing: "plan",
    body: [
      "One continuous floor from the great room to the study, entered through the stone core. Every principal room faces the lake; the study alone turns north to the peaks.",
      "Select a room on the plan to walk to it.",
    ],
    facts: [
      { term: "Great room", value: "152 m²" },
      { term: "Arrival hall", value: "65 m²" },
      { term: "Kitchen and dining", value: "138 m²" },
      { term: "Study", value: "55 m²" },
    ],
  },
  {
    code: "A-301",
    title: "Long section",
    scale: "1:200",
    drawing: "section",
    body: [
      "Cut east to west through all three volumes. The great room rises to 10.4 metres under the ridge; the arrival hall holds a seven-metre void; the bedroom bar cantilevers 2.2 metres over the terrace.",
    ],
    facts: [
      { term: "Ridge", value: "10.4 m" },
      { term: "Arrival hall void", value: "7.0 m" },
      { term: "Cantilever", value: "2.2 m" },
    ],
  },
  {
    code: "A-401",
    title: "Materials",
    scale: "Samples",
    drawing: "materials",
    body: [
      "A short list, used everywhere: split-face limestone outside, honed limestone and oak underfoot, walnut for everything made by hand, dark bronze for every frame.",
    ],
    facts: [
      { term: "Stone", value: "Jura limestone" },
      { term: "Timber", value: "Oak, walnut, charred larch" },
      { term: "Metal", value: "Dark bronze, zinc" },
    ],
  },
  {
    code: "A-501",
    title: "Environmental response",
    scale: "1:200",
    drawing: "environment",
    body: [
      "The bedroom bar overhangs the kitchen by 2.2 metres. At midsummer noon its shadow falls on the terrace, short of the glass; in midwinter the sun passes beneath it and reaches nearly seven metres into the room.",
      "Triple glazing, a ground-source heat pump and a lake-water cooling loop keep the house at 21 °C without a visible plant room.",
    ],
    facts: [
      { term: "Heating demand", value: "28 kWh/m²·yr" },
      { term: "Glazing", value: "Uw 0.6 W/m²K" },
      { term: "Solar roof", value: "24 kWp" },
    ],
  },
];

export const MATERIALS = [
  { id: "stone_ext", name: "Split-face limestone", use: "Plinth and core" },
  { id: "limestone_floor", name: "Honed limestone", use: "Arrival hall floor" },
  { id: "oak_floor", name: "European oak", use: "Floors and ceilings" },
  { id: "walnut", name: "American walnut", use: "Joinery and doors" },
  { id: "marble", name: "Calacatta marble", use: "Kitchen island" },
  { id: "metal_dark", name: "Dark bronze", use: "Window frames" },
  { id: "charred", name: "Charred larch", use: "Bedroom bar cladding" },
  { id: "zinc", name: "Standing-seam zinc", use: "Gable roof" },
];
