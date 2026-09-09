// Landmarks used for nearest‑landmark snapping
export const LANDMARKS = [
  { name: 'Kalinga Hospital Junction', lat: 20.3147, lon: 85.8203 },
  { name: 'Jaydev Vihar', lat: 20.3100, lon: 85.8150 },
  { name: 'Damana', lat: 20.3050, lon: 85.8180 },
  { name: 'Acharya Vihar', lat: 20.3125, lon: 85.8225 },
  { name: 'Chandrasekharpur', lat: 20.3170, lon: 85.8250 },
];

export const findNearestLandmark = ([lat, lon]) => {
  const distance = (a) => Math.hypot(a.lat - lat, a.lon - lon);
  const nearest = LANDMARKS.reduce(
    (prev, cur) => (distance(cur) < distance(prev) ? cur : prev),
    LANDMARKS[0]
  );
  return nearest.name;
};
