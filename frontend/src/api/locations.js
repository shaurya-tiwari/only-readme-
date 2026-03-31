import client from "./client";

export const locationsApi = {
  cities: () => client.get("/api/locations/cities"),
  zones: (citySlug) => client.get("/api/locations/zones", { params: citySlug ? { city_slug: citySlug } : {} }),
  config: () => client.get("/api/locations/config"),
};
