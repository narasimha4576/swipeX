function slug(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function OtherPortals({ query, location }) {
  const q = (query || "").trim();
  const place = (location || "").trim();
  const links = [
    [
      "LinkedIn",
      "https://www.linkedin.com/jobs/search/?keywords=" +
        encodeURIComponent(q || "internship") +
        "&location=" +
        encodeURIComponent(place || "India"),
    ],
    [
      "Indeed India",
      "https://in.indeed.com/jobs?q=" + encodeURIComponent(q || "internship") + "&l=" + encodeURIComponent(place),
    ],
    [
      "Naukri",
      "https://www.naukri.com/" + slug(q || "fresher") + "-jobs" + (place ? "-in-" + slug(place) : ""),
    ],
    ["Internshala", "https://internshala.com/internships/"],
    ["Apprenticeship India", "https://www.apprenticeshipindia.gov.in/"],
  ];

  return (
    <div className="glass card portals">
      <h3>Search other portals</h3>
      <p className="muted small">
        These buttons open each portal's own search in a new tab. SwipeX does not copy their
        listings, so check a job's safety details before you share anything.
      </p>
      <div className="actions">
        {links.map(([label, url]) => (
          <a key={label} className="btn small" href={url} target="_blank" rel="noreferrer">
            {label}
          </a>
        ))}
      </div>
    </div>
  );
}