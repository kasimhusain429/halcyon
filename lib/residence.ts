/**
 * Halcyon — content and choreography data.
 * Areas and heights are measured from the Blender model (blender/arch.py).
 */

export type ShotId = "arrival" | "great" | "kitchen" | "study";

export type Fact = { term: string; value: string };

export type Chapter = {
  id: ShotId | "threshold" | "aerial";
  stop: string; // short name on the route line
  title: string;
  body: string;
  facts: Fact[];
};

export const RESIDENCE = {
  name: "Halcyon",
  place: "Lake Serein",
  tagline: "A private residence on the north shore of Lake Serein.",
  summary:
    "Five bedrooms in 760 m² of limestone, oak and glass, set on 2.6 hectares of shoreline below the Serein range.",
  coordinates: "46.512° N, 9.874° E",
  elevation: "1,268 m",
};

export const CHAPTERS: Chapter[] = [
  {
    id: "threshold",
    stop: "Lake",
    title: "Across still water",
    body: "The house is first seen from the lake, as it was drawn: the glass gable lit like a lantern at dusk, the peaks still holding the last of the sun.",
    facts: [
      { term: "Shoreline", value: "184 m" },
      { term: "Elevation", value: "1,268 m" },
    ],
  },
  {
    id: "aerial",
    stop: "Above",
    title: "Three volumes on a plinth",
    body: "A glass gable for gathering, a limestone core for arriving, a timber bar for sleeping. The plinth becomes terrace, pool edge and the steps down to a private dock.",
    facts: [
      { term: "Pool", value: "13.6 × 4.6 m" },
      { term: "Terraces", value: "360 m²" },
      { term: "Dock", value: "17 m, cedar" },
    ],
  },
  {
    id: "arrival",
    stop: "Arrival hall",
    title: "The arrival hall",
    body: "A seven-metre void in honed limestone and oak. Sixteen floating treads climb the east wall towards the bedroom gallery.",
    facts: [
      { term: "Ceiling", value: "7.0 m" },
      { term: "Floor", value: "Honed limestone" },
      { term: "Door", value: "1.6 × 3.5 m walnut pivot" },
    ],
  },
  {
    id: "great",
    stop: "Great room",
    title: "The great room",
    body: "Oak rafters rise to ten metres over a room that faces the water. The hearth runs the length of the west wall; the gable is glass from floor to ridge.",
    facts: [
      { term: "Area", value: "152 m²" },
      { term: "Ridge height", value: "10.4 m" },
      { term: "Glazed gable", value: "62 m²" },
    ],
  },
  {
    id: "kitchen",
    stop: "Kitchen",
    title: "The kitchen",
    body: "Walnut joinery, a five-metre Calacatta island and a dining table for ten beside the sliding wall to the covered terrace.",
    facts: [
      { term: "Area", value: "138 m²" },
      { term: "Island", value: "5.0 m Calacatta" },
      { term: "Terrace", value: "Covered, 2.2 m cantilever" },
    ],
  },
  {
    id: "study",
    stop: "Study",
    title: "The study",
    body: "A walnut library eleven metres long, and a single window framing the peaks. The drawings for the house are kept here.",
    facts: [
      { term: "Area", value: "55 m²" },
      { term: "Shelving", value: "88 bays, walnut" },
    ],
  },
];

export const NAV = [
  { href: "#walkthrough", label: "Walk through" },
  { href: "#drawings", label: "Drawings" },
  { href: "#stills", label: "Stills" },
  { href: "#viewing", label: "Private viewing" },
];
